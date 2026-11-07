"""Read-only final resource/fixture inspection before stopping owned processes."""
import importlib.util,json,urllib.request
from pathlib import Path
R=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('b',R/'acceptance/stage3/probe-f021-v174-base.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
e=R/'acceptance/stage3/evidence'
sources=[json.loads((e/name).read_text(encoding='utf8')) for name in ['SRS_F021-V1.174-http-20261107.json']]
ids=sorted(set(t for x in sources for t in x['taskIds']));allids=','.join(map(str,ids));defs=[i for x in sources for i in x['definitionIds']]
x={'tag':'V1.174','productSha':b.SHA,'observedAt':b.now(),'taskIds':ids,'taskCount':len(ids),'definitions':defs,'health':json.load(urllib.request.urlopen('http://127.0.0.1:18129/actuator/health')),'activeAssignments':b.sql(f"select count(*) from {b.SC}.task_step_assignments where task_id in ({allids}) and step_status in ('PENDING_ASSIGNMENT','EXECUTING')"),'deviceOccupancy':b.sql(f"select count(*) from {b.SC}.device_agents a join {b.SC}.devices d on a.device_id=d.id where d.device_code like 'G160_F016_%' and a.current_task_id is not null"),'ownedDevices':b.rows(f"select row_to_json(d)::text from {b.SC}.devices d where device_code like 'G160_F016_%'"),'definitionsDisabled':b.sql(f"select count(*) from {b.SC}.task_definitions where id in ({','.join(map(str,defs))}) and definition_status='DISABLED'"),'injectionTriggers':b.sql(f"select count(*) from information_schema.triggers where trigger_schema={b.lit(b.SC)} and trigger_name like 'gpt_%'"),'cleanupRound1':sources[0]['cleanup'],'noRiskRuleOrTemplateChanges':True,'sharedServersStopped':False}
# Configuration includes token hash/encrypted copies in the devices table.
# Export only fields needed to show cleanup; never export token/credential columns.
allow={'device_code','device_status','device_name','area_code','id'}
x['ownedDevices']=[{k:v for k,v in d.items() if k in allow} for d in x['ownedDevices']]
(e/'SRS_F021-V1.174-cleanup-smoke-20261107.json').write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
assert x['activeAssignments']=='0' and x['deviceOccupancy']=='0' and x['definitionsDisabled']==str(len(defs)) and x['injectionTriggers']=='0'
assert all(d['device_status']=='INACTIVE' for d in x['ownedDevices'])
print('Resources restored; taskCount',len(ids),'definitionsDisabled',len(defs),'activeAssignments0 deviceOccupancy0 injectionTriggers0')
