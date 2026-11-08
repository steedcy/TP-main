"""Read-only post-cleanup audit of GPT-owned resources; no state synthesis."""
import importlib.util,json
from pathlib import Path
p=Path(__file__).with_name('probe-f023-v182-runtime.py');s=importlib.util.spec_from_file_location('runtime182audit',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
h=json.loads((m.E/(m.PREFIX+'http-sql-protocol-20261108.json')).read_text(encoding='utf8'))
cfg=m.b.l.API('配置管理员');op=m.b.l.API('运行操作员');ids=','.join(str(x['id']) for x in h['roundTasks'])
agents=m.rows(f"select a.*,d.device_code,d.device_status,d.device_name,d.position_x,d.position_y from {m.SC}.device_agents a join {m.SC}.devices d on d.id=a.device_id where d.device_code in ('G180_F023_0','G145_F013_DISPLAY','G175_F022_FLIGHT') order by a.id")
pending=m.rows(f"select id,task_id,step_status from {m.SC}.task_step_assignments where step_status in ('PENDING_ASSIGNMENT','EXECUTING') order by id")
current=int(m.sql(f"select count(*) from {m.SC}.task_step_assignments where task_id in ({ids}) and step_status in ('PENDING_ASSIGNMENT','EXECUTING')"))
occupied=int(m.sql(f'select count(*) from {m.SC}.device_agents where current_task_id is not null'))
triggers=m.rows(f"select trigger_name,event_object_table from information_schema.triggers where trigger_schema={m.lit(m.SC)}")
risk=next(r for r in cfg('/risk-rules') if r['ruleCode']=='RULE_RESOURCE_CRITICAL')
devices=[];config_ok=True
for item in h['originalConfiguration']:
 d=cfg('/devices/'+item['code']);restored={k:d.get(k) for k in item['body']}
 caps=m.rows(f"select id,capability_status from {m.SC}.device_capabilities where device_id=(select id from {m.SC}.devices where device_code={m.lit(item['code'])}) order by id")
 config_ok &= restored==item['body'] and sorted(caps,key=lambda x:x['id'])==sorted(item['capabilities'],key=lambda x:x['id'])
 devices.append({'code':item['code'],'body':restored,'capabilities':caps})
tasks=m.rows(f'select id,status,current_plan_version_id from {m.SC}.tasks where id in ({ids}) order by id')
checks={'currentPendingZero':current==0,'occupiedZero':occupied==0,'allTasksTerminal':all(t['status'] in ['COMPLETED','FAILED','MANUAL_TERMINATED'] for t in tasks),'historical26RowsUnchanged':pending==h['initialPendingRows'] and len(pending)==26,'allOwnedInactive':len(agents)==3 and all(a['device_status']=='INACTIVE' and a['agent_status']=='DISABLED' for a in agents),'allOwnedReferencesEmpty':all(a['current_task_id'] is None and a['current_step_seq'] is None for a in agents),'ruleContentEnabledRestored':all(risk[k]==h['originalRisk'][k] for k in ['ruleContent','enabled']),'configRestored':config_ok,'noTriggers':not triggers}
v={'at':m.now(),'tag':'V1.182','productSha':m.SHA,'ownedAgentRows':agents,'tasks':tasks,'currentPendingAssignments':current,'occupiedAgents':occupied,'injectionTriggers':triggers,'originalPendingRows':h['initialPendingRows'],'finalPendingRows':pending,'originalRisk':h['originalRisk'],'restoredRisk':risk,'originalConfiguration':h['originalConfiguration'],'restoredDevices':devices,'health':m.b.l.request('http://127.0.0.1:18129/actuator/health'),'snapshot':op('/situation/snapshot'),'checks':checks}
m.save('cleanup-final',v);print(checks);assert all(checks.values())
