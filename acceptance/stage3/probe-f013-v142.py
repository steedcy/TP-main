"""F013 V1.142 real HTTP and persistence probe; no product changes or credentials in output."""
import importlib.util,json,urllib.request,urllib.error
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OLD=ROOT.parent/'tip'
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
l=mod('local',OLD/'scripts/local-test-environment.py');d=mod('db',OLD/'scripts/isolated-reset-db.py')
l.BASE='http://127.0.0.1:18129/api/v1'
SC='tip_gpt_f006_v118_20261030';SHA='28bfb28eef45af0c058bf675e62d2d45b6424102'
def sql(q):return d.sql(d.shared,q)
def raw(api,path,body):
 req=urllib.request.Request(l.BASE+path,json.dumps(body).encode(),{'Content-Type':'application/json','Authorization':'Bearer '+api.token},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=90) as r:return {'http':r.status,'body':json.load(r)}
 except urllib.error.HTTPError as e:return {'http':e.code,'body':json.load(e)}
def observe(api,tid):
 task=api(f'/tasks/{tid}')
 return {'task':task,'plans':api(f'/tasks/{tid}/plan-versions'),'events':api(f'/tasks/{tid}/events'),
 'assignments':api(f'/tasks/{tid}/step-assignments'),
 'commands':sql(f'select id,command_type,command_status from {SC}.device_commands where task_id={tid} order by id').splitlines(),
 'bypassAuditRows':sql(f"select id,operation_type,operation_target,operation_result from {SC}.operation_logs where operation_type='FORCE_BYPASS_ATTEMPT' and operation_target like '{task['taskCode']} -> %' order by id").splitlines()}
def save(name,obj):
 p=ROOT/'acceptance/stage3/evidence'/f'SRS_F013-V1.142-{name}-20261103.json'
 p.write_bytes(json.dumps(obj,ensure_ascii=False,indent=2).encode('utf-8'));return p
def metadata():return {'version':'V1.142','codeSha':SHA,'observedAt':datetime.now().astimezone().isoformat(),'schema':SC}
if __name__=='__main__':
 api=l.API('运行操作员');ev=metadata();ev['cases']=[]
 ev['constraint']=sql(f"select pg_get_constraintdef(oid) from pg_constraint where conrelid='{SC}.operation_logs'::regclass and conname='chk_op_log_result'")
 ev['migration27']=sql(f"select version,success from {SC}.flyway_schema_history where version='27'")
 for tid in [118,119]:
  before=observe(api,tid);case={'taskId':tid,'before':before,'attempts':[]}
  for action in ['FORCE_RELEASE','REQUEST_SUPERVISION']:
   pre=observe(api,tid);body={'action':action,'reason':'F013 V141 synthetic persistence retest'}
   res=raw(api,f'/tasks/{tid}/manual-actions',body);after=observe(api,tid)
   checks={'http400And4110':res['http']==400 and res['body'].get('code')==4110,'pendingManual':after['task']['status']=='PENDING_MANUAL',
    'zeroAssignmentsAndCommands':not after['assignments'] and not after['commands'],
    'newInterceptionEvent':sum(e['eventType']=='FORCE_BYPASS_INTERCEPTED' for e in after['events'])==sum(e['eventType']=='FORCE_BYPASS_INTERCEPTED' for e in pre['events'])+1,
    'newInterceptionAudit':len(after['bypassAuditRows'])==len(pre['bypassAuditRows'])+1 and after['bypassAuditRows'][-1].endswith('|INTERCEPTED'),
    'plansUnchanged':pre['plans']==after['plans']}
   case['attempts'].append({'request':body,'response':res,'after':after,'checks':checks})
   print(json.dumps({'tid':tid,'action':action,'checks':checks}),flush=True)
  ev['cases'].append(case);save('hard-gate-persistence',ev)
