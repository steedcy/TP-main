"""Read-only final resource/config/smoke audit; no database reset or failure cleanup.
Business runners already terminate owned unfinished tasks and deactivate fixtures.
Separate process shutdown is command-line ownership checked and recorded afterward.
"""
import importlib.util,json,hashlib,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];E=R/'acceptance/stage3/evidence'
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('probe-f019-v169.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
raw=list(E.glob('SRS_F019-V1.169-http-20261106*.json'));data=[json.loads(p.read_text(encoding='utf8')) for p in raw];ids=sorted(set(t for d in data for t in d['taskIds']));defs=sorted(set(t for d in data for t in d['definitionIds']));templates=sorted(set(t for d in data for t in d['templateIds']))
op=m.l.API('运行操作员');cfg=m.l.API('配置管理员')
state={'tag':'V1.169','productSha':m.SHA,'at':m.now(),'timezone':'Asia/Shanghai','schema':m.SC,'taskIds':ids,'definitionIds':defs,'templateIds':templates,'health':m.l.request('http://127.0.0.1:18129/actuator/health'),'smoke':{},'heartbeat':cfg('/settings/heartbeat-timeout'),'riskRulesAfter':cfg('/risk-rules'),'riskRulesBefore':data[0]['rulesBefore']}
for name,url in [('tasks','/tasks?page=1&size=1'),('devices','/device-agents?page=1&size=1'),('overview','/dashboard/overview')]:
 try:v=op(url);state['smoke'][name]={'http':200,'nonNullBody':v is not None}
 except Exception as e:state['smoke'][name]={'error':str(e)}
state['tasks']=m.rows(f"select id,task_code,status,current_plan_version_id,replan_used,task_goal from {m.SC}.tasks where id in ({','.join(map(str,ids))}) order by id")
state['ownedDevices']=m.rows(f"select d.device_code,d.device_status as status,a.agent_code,a.current_task_id,a.work_status from {m.SC}.devices d join {m.SC}.device_agents a on a.device_id=d.id where d.device_code like 'G160_F016_%'")
state['activeAssignments']=m.sql(f"select count(*) from {m.SC}.task_step_assignments where task_id in ({','.join(map(str,ids))}) and step_status in ('EXECUTING','PENDING_ASSIGNMENT')")
state['definitions']=m.rows(f"select id,definition_status as status from {m.SC}.task_definitions where id in ({','.join(map(str,defs))})")
state['templates']=m.rows(f"select id,template_status as status from {m.SC}.baseline_templates where id in ({','.join(map(str,templates))})")
state['exceptions']=m.rows(f"select task_id,exception_status,recovery_result,reason_code from {m.SC}.task_exceptions where task_id in ({','.join(map(str,ids))}) order by id")
before={x['ruleCode']:x for x in state['riskRulesBefore']};after={x['ruleCode']:x for x in state['riskRulesAfter']}
state['scopedFaultTriggersRemaining']=m.sql("select count(*) from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname="+m.lit(m.SC)+" and t.tgname='gpt_f169_startup_fault'")
state['checks']={'allOwnedTasksRetained':len(state['tasks'])==len(ids),'allOwnedTasksTerminal':all(t['status'] in ['COMPLETED','FAILED','MANUAL_TERMINATED'] for t in state['tasks']),'noActiveAssignments':state['activeAssignments']=='0','noOwnedAgentOccupation':all(x['current_task_id'] is None and x['work_status']=='IDLE' for x in state['ownedDevices']),'ownedDevicesInactive':all(x['status']=='INACTIVE' for x in state['ownedDevices']),'definitionsDisabled':all(x['status']=='DISABLED' for x in state['definitions']),'templatesDisabled':all(x['status']=='DISABLED' for x in state['templates']),'riskEnableRestored':all(before[k]['enabled']==after[k]['enabled'] for k in before),'heartbeatUnchanged':state['heartbeat']['seconds']==30,'faultTriggerRemoved':state['scopedFaultTriggersRemaining']=='0','healthUp':state['health']['status']=='UP','authenticatedSmoke':all(x.get('http')==200 for x in state['smoke'].values())}
state['jarSha256']=hashlib.sha256((R/'backend/target/airport-ai-app-1.0.0.jar').read_bytes()).hexdigest();state['productSourcesDiff']=subprocess.check_output(['git','diff','V1.169','--','backend/src/main','frontend/src'],cwd=R,encoding='utf8')
(E/'SRS_F019-V1.169-cleanup-smoke-20261106.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8');print(state['checks'])
