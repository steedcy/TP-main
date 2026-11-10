"""Start isolated backend for SRS_NF018 V1.193 verification (port 18130, schema tip_gpt_nf018_v193_20261110, redis db 11).
Does NOT override management exposure: verifies the product's own application.yml."""
import importlib.util, json, socket, subprocess, time, urllib.request, sys
sys.dont_write_bytecode = True
from pathlib import Path
root = Path(__file__).resolve().parents[3]
old = root.parent / 'tip'
def mod(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
db = mod('db', old / 'scripts/isolated-reset-db.py')
schema = 'tip_gpt_nf018_v193_20261110'; port = 18130
db.sql(db.shared, f'CREATE SCHEMA IF NOT EXISTS {schema}')
with socket.socket() as s:
    assert s.connect_ex(('127.0.0.1', port)) != 0, 'port busy'
env = db.variables.copy()
env.update(
    SPRING_DATASOURCE_URL=f"jdbc:postgresql://{env.get('DB_HOST','localhost')}:{env.get('DB_PORT','5432')}/{db.shared}?currentSchema={schema}&ApplicationName=GPT_NF018_V193",
    SPRING_FLYWAY_SCHEMAS=schema, SERVER_ADDRESS='127.0.0.1', SERVER_PORT=str(port),
    SPRING_DATA_REDIS_DATABASE='11', PLANNING_MODEL_PROVIDER='external',
    PLANNING_MODEL_ENDPOINT='http://127.0.0.1:18117', PLANNING_MODEL_API_KEY='local-fixture')
d = root / '.local-test'; d.mkdir(parents=True, exist_ok=True)
log = (d / 'backend-nf018-v193.log').open('wb', buffering=0)
p = subprocess.Popen(['java','-Xms32m','-Xmx256m','-XX:+UseSerialGC','-jar',str(root/'backend/target/airport-ai-app-1.0.0.jar')],
    cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008)
(d / 'runtime-nf018-v193.json').write_text(json.dumps({'pid': p.pid, 'port': port, 'schema': schema}))
print('pid', p.pid)
for _ in range(120):
    if p.poll() is not None: raise SystemExit(f'exited {p.returncode}')
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/actuator/health', timeout=2) as r:
            print('health', r.status, r.read().decode()[:80]); sys.exit(0)
    except Exception: time.sleep(1)
raise SystemExit('timeout')
