"""Run the packaged JAR without product overrides; preserve startup and health evidence.

Provide the isolated datasource credentials through the environment. Never prints them.
Example: python acceptance/stage3/retest-f015-jar-startup.py --schema <GPT-owned-schema>
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo


def now():
    return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema', required=True)
    parser.add_argument('--port', type=int, default=18129)
    parser.add_argument('--label', default='attempt2')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    jar = root / 'backend/target/airport-ai-app-1.0.0.jar'
    out = root / 'acceptance/stage3/evidence'
    assert 'gpt' in args.schema.lower(), 'Use an explicitly GPT-owned schema'
    env = os.environ.copy()
    assert f'currentSchema={args.schema}' in env.get('SPRING_DATASOURCE_URL', '')
    assert env.get('SPRING_FLYWAY_SCHEMAS') == args.schema
    assert env.get('SPRING_DATA_REDIS_DATABASE') == '10'
    env.update(SERVER_ADDRESS='127.0.0.1', SERVER_PORT=str(args.port))
    with socket.socket() as sock:
        assert sock.connect_ex(('127.0.0.1', args.port)) != 0, 'Port is already occupied'
    prefix = out / f'SRS_F015-V1.152-startup-{args.label}-20261104'
    log_path = Path(str(prefix) + '.txt')
    json_path = Path(str(prefix) + '.json')
    assert not log_path.exists() and not json_path.exists(), 'Do not overwrite raw evidence'
    command = ['java', '-Xms32m', '-Xmx192m', '-XX:TieredStopAtLevel=1',
               '-XX:+UseSerialGC', '-jar', str(jar)]
    evidence = {
        'startedAt': now(), 'timezone': 'Asia/Shanghai',
        'productSha': 'd86a722e2e56869f279ae25c82bcb6ab6d8ee30d',
        'tag': 'V1.152', 'schema': args.schema, 'redisDb': 10,
        'port': args.port, 'command': command,
        'jarSha256': hashlib.sha256(jar.read_bytes()).hexdigest(),
        'health': [], 'businessEntry': None,
        'expected': 'Production JAR starts; health UP and authentication endpoint reachable',
    }
    try:
        with log_path.open('wb') as log:
            proc = subprocess.Popen(command, cwd=root, env=env, stdout=log,
                                    stderr=subprocess.STDOUT,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            evidence['pid'] = proc.pid
            deadline = time.monotonic() + 60
            while proc.poll() is None and time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(
                        f'http://127.0.0.1:{args.port}/actuator/health', timeout=1
                    ) as response:
                        evidence['health'].append({'at': now(), 'http': response.status,
                                                   'body': json.load(response)})
                except Exception as exc:
                    evidence['health'].append({'at': now(), 'errorType': type(exc).__name__})
                time.sleep(0.5)
            evidence['exitCode'] = proc.poll()
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=10)
                evidence['stoppedByProbe'] = True
        try:
            request = urllib.request.Request(
                f'http://127.0.0.1:{args.port}/api/v1/auth/login', b'{}',
                {'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(request, timeout=2) as response:
                evidence['businessEntry'] = {'http': response.status}
        except Exception as exc:
            evidence['businessEntry'] = {'errorType': type(exc).__name__}
        log_text = log_path.read_text(encoding='utf-8', errors='replace')
        evidence['checks'] = {
            'exitedNonzero': evidence['exitCode'] not in (None, 0),
            'taskExceptionBeanFailure': "bean with name 'taskExceptionService'" in log_text,
            'noDefaultConstructor': 'No default constructor found' in log_text,
            'missingConstructorRootCause': 'TaskExceptionService.<init>()' in log_text,
            'healthNeverUp': not any(x.get('body', {}).get('status') == 'UP'
                                    for x in evidence['health']),
        }
        evidence['actual'] = 'Spring ApplicationContext fails before the HTTP service is ready'
    finally:
        with socket.socket() as sock:
            evidence['portReleased'] = sock.connect_ex(('127.0.0.1', args.port)) != 0
        evidence['finishedAt'] = now()
        json_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'evidence': str(json_path), 'checks': evidence.get('checks'),
                      'exitCode': evidence.get('exitCode')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
