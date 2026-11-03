"""Independent HTTP/DB probe. Uses only GPT's schema and local controlled model.
Credentials are loaded from local-test-environment; never written to evidence.
Run in GPT worktree with a V1.140 backend on 18129 and controlled model on 18117.
"""
import importlib.util,json,urllib.request,urllib.error
from datetime import datetime
from pathlib import Path
root=Path(__file__).resolve().parents[2]
old=root.parent/'tip'
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
l=mod('local',old/'scripts/local-test-environment.py');d=mod('db',old/'scripts/isolated-reset-db.py')
l.BASE='http://127.0.0.1:18129/api/v1';api=l.API('运行操作员')
sc='tip_gpt_f006_v118_20261030'
def sql(q):return d.sql(d.shared,q)
def raw(path,body):
 req=urllib.request.Request(l.BASE+path,json.dumps(body).encode(),{'Content-Type':'application/json','Authorization':'Bearer '+api.token},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=90) as r:return {'http':r.status,'body':json.load(r)}
 except urllib.error.HTTPError as e:return {'http':e.code,'body':json.load(e)}
def observe(tid):
 task=api(f'/tasks/{tid}')
 return {'task':task,'plans':api(f'/tasks/{tid}/plan-versions'),'events':api(f'/tasks/{tid}/events'),
 'assignments':api(f'/tasks/{tid}/step-assignments'),
 'commands':sql(f'select id,command_type,command_status from {sc}.device_commands where task_id={tid} order by id').splitlines(),
 'bypassAuditRows':sql(f"select id,operation_type,operation_target,operation_result from {sc}.operation_logs where operation_type='FORCE_BYPASS_ATTEMPT' and operation_target like '{task['taskCode']} -> %' order by id").splitlines()}
ev={'version':'V1.140','codeSha':'2ff5c6e5c0db097c6b8e6db68e44d964fc8c822c','handoffSha':'2d42333878e31c776265d7f4f35d105eb713c76c','observedAt':datetime.now().astimezone().isoformat(),'schema':sc,'cases':[]}
for name in ['F012_MISSING_PRE','F012_LOOP_PRE']:
 req={'taskGoal':name+' F013 independent hard-gate test','taskFamily':'EXT_2AD8B934','sceneParams':{'targetLocation':'F2_TEST_GATE'}}
 task=api('/tasks','POST',req);tid=task['id']
 case={'modelFixture':name,'submitRequest':req,'before':observe(tid),'attempts':[]}
 assert case['before']['task']['status']=='PENDING_MANUAL'
 for action in ['FORCE_RELEASE','REQUEST_SUPERVISION']:
  body={'action':action,'reason':'F013 synthetic independent bypass rejection probe'}
  res=raw(f'/tasks/{tid}/manual-actions',body);after=observe(tid)
  checks={'rejected4110':res['body'].get('code')==4110,
   'pendingManual':after['task']['status']=='PENDING_MANUAL',
   'zeroAssignmentsAndCommands':not after['assignments'] and not after['commands'],
   'noSupervisionEvents':not any(e['eventType'] in ['SUPERVISION_STARTED','SUPERVISION_COMPLETED'] for e in after['events']),
   'interceptionEventPersisted':any(e['eventType']=='FORCE_BYPASS_INTERCEPTED' for e in after['events']),
   'interceptionAuditPersisted':bool(after['bypassAuditRows'])}
  case['attempts'].append({'request':body,'response':res,'after':after,'checks':checks})
  print(json.dumps({'taskId':tid,'action':action,'checks':checks},ensure_ascii=False),flush=True)
 ev['cases'].append(case)
 out=root/'acceptance/stage3/evidence/SRS_F013-V1.140-hard-gate-audit-20261103.json'
 out.write_text(json.dumps(ev,ensure_ascii=False,indent=2),encoding='utf-8')
print('evidence',out)
