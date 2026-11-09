"""Start local test backend for SRS_F028 V1.189 verification.
Isolated schema: tip_gpt_f006_v118_20261030, Redis db: 10, Port: 18129.
"""
import importlib.util, json, socket, subprocess, time, urllib.request, sys
sys.dont_write_bytecode = True
from pathlib import Path

root = Path(__file__).resolve().parents[3]
old = root.parent / 'tip'

def mod(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

db = mod('db', old / 'scripts/isolated-reset-db.py')
schema = 'tip_gpt_f006_v118_20261030'
port = 18129

with socket.socket() as s:
    assert s.connect_ex(('127.0.0.1', port)) != 0, f'Port {port} already occupied'

env = db.variables.copy()
env.update(
    SPRING_DATASOURCE_URL=f"jdbc:postgresql://{env.get('DB_HOST','localhost')}:{env.get('DB_PORT','5432')}/{db.shared}?currentSchema={schema}&ApplicationName=GPT_F028_V189",
    SPRING_FLYWAY_SCHEMAS=schema,
    SERVER_ADDRESS='127.0.0.1',
    SERVER_PORT=str(port),
    SPRING_DATA_REDIS_DATABASE='10',
    APP_DEVICE_ADAPTER_PUBLIC_BASE_URL=f'http://127.0.0.1:{port}',
    APP_DEVICE_PRESET_AREAS='F2_TEST,F2_ZONE_A,F2_ZONE_B',
    APP_CONTEXT_FAULT_INJECTION_FAILED_AGENT_CODES='',
    APP_DEVICE_MAX_ACCESS_OBJECTS_SYSTEM='30'
)

log_path = root / '.local-test/backend-v189.log'
log = log_path.open('wb', buffering=0)

jar_path = root / 'backend/target/airport-ai-app-1.0.0.jar'
assert jar_path.exists(), f'JAR not found: {jar_path}'

p = subprocess.Popen(
    ['java', '-Xms32m', '-Xmx192m', '-XX:TieredStopAtLevel=1', '-XX:+UseSerialGC', '-jar', str(jar_path)],
    cwd=root,
    env=env,
    stdout=log,
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW
)

runtime_info = {'pid': p.pid, 'port': port, 'schema': schema, 'version': 'V1.189'}
(root / '.local-test/runtime-v189.json').write_text(json.dumps(runtime_info), encoding='utf-8')

print(f'Starting backend on port {port}, pid {p.pid}...')
for _ in range(90):
    if p.poll() is not None:
        raise RuntimeError(f'Backend process exited early with code {p.returncode}')
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/actuator/health', timeout=2) as r:
            if json.load(r).get('status') == 'UP':
                print(f'Backend healthy on port {port}, PID {p.pid}')
                sys.exit(0)
    except Exception:
        time.sleep(1)

raise RuntimeError('Backend health check timed out after 90 seconds')
