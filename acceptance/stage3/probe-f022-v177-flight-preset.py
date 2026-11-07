"""Complete flight-preset prerequisite with own existing flight adapter; no NAV interference."""
import os,importlib.util,json,copy
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='flight-preset'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f022-v177-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;m=r.m;SC=r.SC
row=r.case('flight-preset-current-edit-restore');dev=m.Device('G175_F022_FLIGHT',18135);dev.simtype='FLIGHT_DELAY_BOARD';dev.healthcaps=['CAP_INFO_DISPLAY','CAP_FLIGHT_UPDATE'];q.devices.append(dev)
caps=m.rows(f'select id,capability_type,capability_status from {SC}.device_capabilities order by id');row['originalCapabilities']=caps
d=next(v for v in q.cfg('/task-definitions') if v['isPreset'] and v['definitionCode']=='FLIGHT_CHANGE_RESPONSE');original=m.rows(f"select * from {SC}.task_definitions where id={d['id']}")[0];row['before']=d
try:
 dev.token=q.cfg(f'/devices/{dev.code}/device-token/rotate','POST')['accessToken'];q.cfg(f'/devices/{dev.code}/connection-test','POST');q.cfg(f'/devices/{dev.code}/status','POST',{'status':'ACTIVE'});q.cfg(f'/devices/{dev.code}/connection-test','POST');dev.heartbeat()
 row['capabilityTest']=q.cfg(f'/devices/{dev.code}/capabilities/CAP_FLIGHT_UPDATE/test','POST');q.cfg(f'/devices/{dev.code}/capabilities/CAP_FLIGHT_UPDATE/status','POST',{'status':'ENABLED'})
 m.sql(f"update {SC}.device_capabilities set capability_status='ENABLED' where id in (select min(id) from {SC}.device_capabilities group by capability_type)")
 b=r.payload(d);edit=copy.deepcopy(b);edit['constraintDescription']='G177 flight preset edit';edit['sceneParams'].append({'name':'g177Optional','type':'String','required':False,'range':'synthetic edit'})
 row['delete']=r.raw(q.cfg,f'/task-definitions/{d["id"]}',None,'DELETE');row['identityChange']=r.raw(q.cfg,f'/task-definitions/{d["id"]}',dict(edit,taskName='FORBIDDEN',definitionCode='FORBIDDEN'),'PUT')
 try:row['edited']=q.cfg(f'/task-definitions/{d["id"]}','PUT',edit)
 finally:row['restored']=q.cfg(f'/task-definitions/{d["id"]}','PUT',b);q.save()
 r.record(row,{'actualCapabilityTestPassed':row['capabilityTest']['capabilityStatus']=='TESTED_PASSED','delete400':row['delete']['http']==400,'identityRejected':row['identityChange']['http']==400,'constraintAndParamEditable':row['edited']['constraintDescription']=='G177 flight preset edit' and row['edited']['sceneParams'][-1]['name']=='g177Optional','identityPreserved':row['edited']['taskName']==d['taskName'] and row['edited']['definitionCode']==d['definitionCode']})
finally:
 m.sql(f"update {SC}.task_definitions set scene_params={m.lit(json.dumps(original['scene_params'],ensure_ascii=False))}::json where id={d['id']}")
 for c in caps:m.sql(f"update {SC}.device_capabilities set capability_status={m.lit(c['capability_status'])} where id={c['id']}")
 row['restoredRows']=m.rows(f"select * from {SC}.task_definitions where id={d['id']}");row['restoredCapabilities']=m.rows(f'select id,capability_type,capability_status from {SC}.device_capabilities order by id');q.cleanup();q.ev['endedAt']=m.now();q.save()
