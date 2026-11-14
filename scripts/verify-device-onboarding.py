"""Isolated local HTTP/SQL/process smoke for automatic device onboarding.

Build backend and simulator first. Requires Windows PostgreSQL psql, Java 17,
and existing local DB/Redis connection settings. Never modifies public tables,
flushes Redis, or stops an unowned process. Evidence excludes access tokens.
"""
import datetime
import importlib.util
import json
import os
import pathlib
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local-test' / 'onboarding-smoke'
LOCAL.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('localenv', ROOT / 'scripts/local-test-environment.py')
localenv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(localenv)
ENV = localenv.env()
SCHEMA = 'tip_onboarding_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + secrets.token_hex(3)
PORT = 18380
BASE = f'http://127.0.0.1:{PORT}'
PSQL = shutil.which('psql') or r'C:\Program Files\PostgreSQL\15\bin\psql.exe'
DATABASE = ENV.get('DB_NAME', 'airport_ai')
if ENV.get('DB_PASSWORD'):
    ENV['PGPASSWORD'] = ENV['DB_PASSWORD']
TOKEN = None
CREATED = []
OBSERVATIONS = []


def sql(query, scoped=True):
    prefix = f'SET search_path TO {SCHEMA}; ' if scoped else ''
    command = [PSQL, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-h', ENV.get('DB_HOST', 'localhost'),
               '-p', ENV.get('DB_PORT', '5432'), '-U', ENV.get('DB_USERNAME', 'admin'), '-d', DATABASE]
    result = subprocess.run(command, input=prefix + query, env=ENV, text=True, encoding='utf-8', capture_output=True)
    if result.returncode:
        raise RuntimeError('isolated SQL failed: ' + result.stderr[-500:])
    return result.stdout.strip()


def request(path, method='GET', data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    body = None if data is None else json.dumps(data).encode()
    url = path if path.startswith('http') else BASE + path
    try:
        with urllib.request.urlopen(urllib.request.Request(url, body, headers, method=method), timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def api(path, method='GET', data=None, expected=200):
    status, response = request('/api/v1' + path, method, data, TOKEN)
    assert status == expected, (path, status, response.get('message'))
    return response.get('data')


def note(name, **details):
    OBSERVATIONS.append({'name': name, 'passed': True, **details})
    print(name + ': passed', flush=True)


def wait_device(code, expected='READY', timeout=150):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        device = api('/devices/' + code)
        state = device['onboardingStatus']
        if state == expected:
            return device
        if state == 'FAILED' and expected != 'FAILED':
            raise AssertionError((code, device['onboardingMessage']))
        time.sleep(1)
    raise AssertionError((code, 'onboarding timeout'))


def create(code, simulated_type='SMART_DISPLAY', **overrides):
    body = dict(deviceCode=code, deviceName='Synthetic ' + code, deviceTypeCode='SIMULATOR', isSimulator=True,
                simulatedDeviceType=simulated_type, areaCode='F2_TEST', positionX=12.25, positionY=34.5,
                accessEndpoint='', accessCredentialRef='', statusReportInterval=5)
    body.update(overrides)
    device = api('/devices', 'POST', body)
    CREATED.append(code)
    assert device['deviceTokenConfigured'] is True
    assert all(name not in device for name in ('accessToken', 'deviceTokenHash', 'deviceTokenCiphertext'))
    return device


def main():
    global TOKEN
    with socket.socket() as guard:
        guard.bind(('127.0.0.1', PORT))  # refuses to interfere with an existing service
    assert SCHEMA.startswith('tip_onboarding_') and SCHEMA != 'public'
    sql('CREATE SCHEMA ' + SCHEMA, scoped=False)
    environment = ENV.copy()
    environment.update(SERVER_PORT=str(PORT),
        SPRING_DATASOURCE_URL=f"jdbc:postgresql://{ENV.get('DB_HOST', 'localhost')}:{ENV.get('DB_PORT', '5432')}/{DATABASE}?currentSchema={SCHEMA}",
        SPRING_FLYWAY_SCHEMAS=SCHEMA, SPRING_FLYWAY_DEFAULT_SCHEMA=SCHEMA,
        SPRING_DATA_REDIS_DATABASE='15', DEVICE_CREDENTIAL_ENCRYPTION_KEY=secrets.token_urlsafe(48),
        DEVICE_PLATFORM_BASE_URL=BASE, DEVICE_SIMULATOR_JAR=str(ROOT / 'simulator/target/device-simulator-runtime.jar'),
        APP_DEVICE_PRESET_AREAS='F2_TEST', PLANNING_MODEL_PROVIDER='external', PLANNING_MODEL_ENDPOINT='http://127.0.0.1:18499')
    backend = None
    op_token = None
    completed = False
    failure = None
    try:
        log = open(LOCAL / 'backend.log', 'ab', buffering=0)
        runnable = LOCAL / 'backend-probe.jar'
        shutil.copy2(ROOT / 'backend/target/airport-ai-app-1.0.0.jar', runnable)
        backend = subprocess.Popen([shutil.which('java'), '-Xms64m', '-Xmx384m', '-XX:+UseSerialGC', '-jar',
            str(runnable)], cwd=ROOT, env=environment,
            stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(120):
            if backend.poll() is not None:
                raise RuntimeError('isolated backend exited; inspect local log')
            try:
                if request('/actuator/health')[0] == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        else:
            raise RuntimeError('isolated backend did not become ready')

        password = secrets.token_urlsafe(15)
        environment['ONBOARDING_PROBE_PASSWORD'] = password
        source = LOCAL / 'ProbeHash.java'
        source.write_text('import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder; '
            'class ProbeHash { public static void main(String[] x) { System.out.print(new BCryptPasswordEncoder().encode(System.getenv("ONBOARDING_PROBE_PASSWORD"))); }}')
        repository = pathlib.Path.home() / '.m2/repository'
        crypto = next(repository.glob('org/springframework/security/spring-security-crypto/*/spring-security-crypto-*.jar'))
        jcl = next(repository.glob('org/springframework/spring-jcl/*/spring-jcl-*.jar'))
        encoded = subprocess.check_output([shutil.which('java'), '-cp', os.pathsep.join(map(str, [crypto, jcl])), str(source)],
                                         env=environment, text=True).strip()
        for name, role in [('onboard_cfg', 'CONFIG_ADMIN'), ('onboard_operator', 'OPERATOR')]:
            sql(f"INSERT INTO users(username,password_hash,real_name,role,contact) VALUES ('{name}','{encoded}','Synthetic','{role}','synthetic@example.invalid')")
        TOKEN = request('/api/v1/auth/login', 'POST', {'username': 'onboard_cfg', 'password': password})[1]['data']['token']
        op_token = request('/api/v1/auth/login', 'POST', {'username': 'onboard_operator', 'password': password})[1]['data']['token']

        codes = []
        kinds = ['SMART_DISPLAY'] if '--quick' in sys.argv else ['SMART_DISPLAY', 'BAGGAGE_SCANNER', 'FLIGHT_DELAY_BOARD', 'MOBILE_ROBOT']
        for index, kind in enumerate(kinds):
            code = 'AUTO_' + str(index)
            create(code, kind)
            codes.append(code)
        endpoints = []
        for code in codes:
            device = wait_device(code)
            assert device['connectionTestStatus'] == 'PASSED'
            endpoints.append(device['accessEndpoint'])
            assert sql(f"SELECT count(*) FROM device_agents a JOIN devices d ON d.id=a.device_id WHERE d.device_code='{code}' AND a.agent_status='ENABLED' AND a.online_status='ONLINE' AND a.last_reported_at IS NOT NULL") == '1'
            note('automatic onboarding ' + code, simulatedType=device['simulatedDeviceType'])
        assert len(set(endpoints)) == len(kinds)
        note('distinct automatically allocated endpoints', count=len(kinds))
        assert sql("SELECT count(*) FROM devices WHERE device_token_hash IS NOT NULL AND device_token_ciphertext IS NOT NULL AND length(device_token_hash)=64") == str(len(kinds))
        assert sql("SELECT count(*) FROM device_capabilities WHERE capability_status='ENABLED'") == '0'
        note('encrypted credentials and untested capabilities remain disabled')

        endpoint = endpoints[0]
        agent_code = sql("SELECT agent_code FROM device_agents a JOIN devices d ON d.id=a.device_id WHERE d.device_code='AUTO_0'")
        first = api('/devices/AUTO_0/device-token/rotate', 'POST')['accessToken']
        wait_device('AUTO_0')
        second = api('/devices/AUTO_0/device-token/rotate', 'POST')['accessToken']
        wait_device('AUTO_0')
        assert first != second
        assert request(endpoint + '/device-api/v1/health?nonce=rotation', token=first)[0] == 401
        assert request(endpoint + '/device-api/v1/health?nonce=rotation', token=second)[0] == 200
        assert sql("SELECT agent_code FROM device_agents a JOIN devices d ON d.id=a.device_id WHERE d.device_code='AUTO_0'") == agent_code
        note('rotation revokes old token, restarts runtime and reuses the same agent')

        request(endpoint + '/device-api/v1/control/heartbeat?value=false', 'POST', token=second)
        sql("UPDATE device_agents SET work_status='BUSY' WHERE agent_code='" + agent_code + "'")
        api('/devices/AUTO_0/onboarding/retry', 'POST', expected=409)
        api('/devices/AUTO_0/device-token/rotate', 'POST', expected=409)
        sql("UPDATE device_agents SET work_status='IDLE' WHERE agent_code='" + agent_code + "'")
        request(endpoint + '/device-api/v1/control/heartbeat?value=true', 'POST', token=second)
        note('busy device rejects restart and rotation')
        for path in ['/devices/AUTO_0/onboarding/retry', '/devices/AUTO_0/device-token/rotate']:
            assert request('/api/v1' + path, 'POST', token=op_token)[0] == 403
        note('operator cannot rotate tokens or restart runtimes')

        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0)); occupied.listen()
            occupied_port = occupied.getsockname()[1]
            create('AUTO_OCCUPIED', accessEndpoint=f'http://127.0.0.1:{occupied_port}')
            failed = wait_device('AUTO_OCCUPIED', 'FAILED')
            assert '\u5360\u7528' in failed['onboardingMessage']
            assert sql("SELECT count(*) FROM device_agents a JOIN devices d ON d.id=a.device_id WHERE d.device_code='AUTO_OCCUPIED'") == '0'
            note('occupied external port is preserved and does not create an agent')
        api('/devices/AUTO_OCCUPIED/onboarding/retry', 'POST')
        wait_device('AUTO_OCCUPIED')
        note('retry recovers the failed device after its port becomes available')
        create('AUTO_REMOTE', accessEndpoint='http://example.invalid:18190')
        wait_device('AUTO_REMOTE', 'FAILED')
        note('remote endpoint fails explicitly without process takeover')
        create('REAL_DEVICE', isSimulator=False, deviceTypeCode='SMART_DISPLAY', simulatedDeviceType=None,
               accessEndpoint='http://example.invalid:18191', accessCredentialRef='synthetic-reference')
        assert api('/devices/REAL_DEVICE')['onboardingStatus'] == 'MANUAL'
        note('physical device receives a token without a simulator process')
        assert sql("SELECT count(*) FROM operation_logs WHERE operation_type='DEVICE_TOKEN_ROTATE'") == '2'
        api('/auth/logout', 'POST')
        TOKEN = request('/api/v1/auth/login', 'POST', {'username': 'onboard_cfg', 'password': password})[1]['data']['token']
        request('/api/v1/auth/logout', 'POST', token=op_token)
        completed = True
    except Exception as error:
        failure = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if op_token:
            try:
                request('/api/v1/auth/logout', 'POST', token=op_token)
            except Exception:
                pass
        if TOKEN:
            for code in CREATED:
                try:
                    api('/devices/' + code, 'DELETE')
                except Exception:
                    pass
            try:
                api('/auth/logout', 'POST')
            except Exception:
                pass
        if backend is not None:
            backend.terminate()
            backend.wait(timeout=20)
        result = {'schema': SCHEMA, 'backendPort': PORT, 'completed': completed, 'failure': failure, 'observations': OBSERVATIONS,
                  'purpose': 'implementation smoke; not independent 95-case acceptance'}
        encoded_result = json.dumps(result, indent=2, ensure_ascii=False)
        (LOCAL / ('result-' + SCHEMA + '.json')).write_text(encoded_result, encoding='utf-8')
        (LOCAL / 'result.json').write_text(encoded_result, encoding='utf-8')


def backend_tests():
    """The legacy observability test disables Flyway: prepare its isolated schema first."""
    import re
    import xml.etree.ElementTree as ET
    sql('CREATE SCHEMA ' + SCHEMA, scoped=False)
    migrations = sorted((ROOT / 'backend/src/main/resources/db/migration').glob('V*__*.sql'),
                        key=lambda path: int(re.match(r'V(\d+)', path.name)[1]))
    sql('BEGIN;\n' + '\n'.join(path.read_text(encoding='utf-8-sig') for path in migrations) + '\nCOMMIT;')
    environment = ENV.copy()
    environment.update(SPRING_DATASOURCE_URL=f"jdbc:postgresql://{ENV.get('DB_HOST', 'localhost')}:{ENV.get('DB_PORT', '5432')}/{DATABASE}?currentSchema={SCHEMA}",
                       SPRING_DATA_REDIS_DATABASE='15')
    with open(LOCAL / 'backend-tests.log', 'w', encoding='utf-8') as log:
        result = subprocess.run([shutil.which('mvn'), '-q', 'package'], cwd=ROOT / 'backend', env=environment,
                                stdout=log, stderr=subprocess.STDOUT)
    totals = dict(tests=0, failures=0, errors=0, skipped=0)
    for path in (ROOT / 'backend/target/surefire-reports').glob('TEST-*.xml'):
        suite = ET.parse(path).getroot()
        for key in totals:
            totals[key] += int(suite.get(key, 0))
    summary = dict(schema=SCHEMA, exitCode=result.returncode, **totals)
    (LOCAL / 'backend-tests-result.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary), flush=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    backend_tests() if '--backend-tests' in sys.argv else main()
