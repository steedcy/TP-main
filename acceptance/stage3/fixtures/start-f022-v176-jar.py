"""Saved equivalent of the local startup helper used for this round.
Run only with the declared GPT-owned existing schema and private isolated DB config.
It uses ../tip/scripts/isolated-reset-db.py solely to read environment (no reset).
Model18117 and simulators are separate owned processes. Stops are operator-owned;
record PID metadata and verify command before stopping process trees. Never commit
private environment, DPAPI secrets or the unredacted backend log.
"""
import importlib.util,json,socket,subprocess,time,urllib.request,sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
old=root.parent/'tip'
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
db=mod('db',old/'scripts/isolated-reset-db.py')
schema='tip_gpt_f006_v118_20261030';port=18129
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0,'GPT backend port occupied'
env=db.variables.copy();env.update(SPRING_DATASOURCE_URL=f"jdbc:postgresql://{env.get('DB_HOST','localhost')}:{env.get('DB_PORT','5432')}/{db.shared}?currentSchema={schema}",SPRING_FLYWAY_SCHEMAS=schema,SERVER_ADDRESS='127.0.0.1',SERVER_PORT=str(port),SPRING_DATA_REDIS_DATABASE='10',PLANNING_MODEL_PROVIDER='external',PLANNING_MODEL_ENDPOINT='http://127.0.0.1:18117',APP_DEVICE_ADAPTER_PUBLIC_BASE_URL='http://127.0.0.1:18129',APP_DEVICE_PRESET_AREAS='F2_TEST,F2_ZONE_A,F2_ZONE_B',APP_CONTEXT_FAULT_INJECTION_FAILED_AGENT_CODES='')
mode=sys.argv[1] if len(sys.argv)>1 else ''
env['SPRING_DATASOURCE_URL']+='&ApplicationName=GPT_F022_V176'
env['APP_RISK_FAULT_INJECTION_MODE']=mode
log=(root/'.local-test/backend-v176.log').open('ab',buffering=0)
p=subprocess.Popen(['java','-Xms32m','-Xmx192m','-XX:TieredStopAtLevel=1','-XX:+UseSerialGC','-jar',str(root/'backend/target/airport-ai-app-1.0.0.jar')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
(root/'.local-test/runtime-v176.json').write_text(json.dumps({'pid':p.pid,'port':port,'schema':schema,'version':'V1.176'}))
for _ in range(120):
 if p.poll() is not None:raise RuntimeError('backend exited')
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{port}/actuator/health',timeout=2) as r:
   if json.load(r).get('status')=='UP':break
 except Exception:time.sleep(1)
else:raise RuntimeError('health timeout')
print('healthy',p.pid)
