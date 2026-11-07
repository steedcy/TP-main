"""Complete missing flight-preset edit prerequisite using an owned flight-display simulator.
Other capability-status fixtures are configuration-only SQL in GPT schema, restored.
"""
import os,importlib.util,copy,json
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='preset-flight'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f022-v175-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)

def normalized(v):
 return {k:normalized(x) for k,x in v.items() if x is not None} if isinstance(v,dict) else [normalized(x) for x in v] if isinstance(v,list) else v

q=r.q;m=r.m;SC=r.SC
row=r.case('flight-preset-prerequisite-and-edit-restore');device=m.Device('G175_F022_FLIGHT',18135);device.simtype='FLIGHT_DELAY_BOARD';device.healthcaps=['CAP_INFO_DISPLAY','CAP_FLIGHT_UPDATE'];q.devices.append(device)
fixture=m.rows(f'select id,capability_status from {SC}.device_capabilities order by id');row['originalCapabilities']=fixture
try:
 body={'deviceCode':device.code,'deviceName':'Synthetic F022 flight prerequisite','deviceTypeCode':'SIMULATOR','isSimulator':True,'simulatedDeviceType':'FLIGHT_DELAY_BOARD','areaCode':'F2_TEST','positionX':0,'positionY':0,'accessEndpoint':'http://127.0.0.1:18135','statusReportInterval':5,'accessCredentialRef':'synthetic-f022'}
 row['created']=q.cfg('/devices','POST',body);device.token=q.cfg(f'/devices/{device.code}/device-token/rotate','POST')['accessToken'];q.cfg(f'/devices/{device.code}/connection-test','POST');q.cfg(f'/devices/{device.code}/status','POST',{'status':'ACTIVE'});q.cfg(f'/devices/{device.code}/connection-test','POST');device.heartbeat()
 row['capabilityTest']=q.cfg(f'/devices/{device.code}/capabilities/CAP_FLIGHT_UPDATE/test','POST');q.cfg(f'/devices/{device.code}/capabilities/CAP_FLIGHT_UPDATE/status','POST',{'status':'ENABLED'})
 m.sql(f"update {SC}.device_capabilities set capability_status='ENABLED' where id in (select min(id) from {SC}.device_capabilities group by capability_type)")
 d=next(x for x in q.cfg('/task-definitions') if x['isPreset'] and x['definitionCode']=='FLIGHT_CHANGE_RESPONSE');row['before']=d;b=r.payload(d);edit=copy.deepcopy(b);edit['constraintDescription']='F175 flight preset edit restore';edit['sceneParams'].append({'name':'f175Optional','type':'String','required':False,'range':'synthetic edit'})
 row['delete']=r.raw(q.cfg,f'/task-definitions/{d["id"]}',None,'DELETE');row['immutableReject']=r.raw(q.cfg,f'/task-definitions/{d["id"]}',dict(edit,taskName='FORBIDDEN_NAME',definitionCode='FORBIDDEN_CODE'),'PUT')
 try:row['updated']=q.cfg(f'/task-definitions/{d["id"]}','PUT',edit)
 finally:row['restored']=q.cfg(f'/task-definitions/{d["id"]}','PUT',b);q.save()
 r.record(row,{'flightCapabilityTestSuccess':row['capabilityTest'].get('capabilityStatus')=='TESTED_PASSED','presetDelete400':row['delete']['http']==400,'identityChangeRejected400':row['immutableReject']['http']==400,'paramsConstraintEditable':row['updated']['constraintDescription']=='F175 flight preset edit restore' and row['updated']['sceneParams'][-1]['name']=='f175Optional','identityUnchanged':row['updated']['taskName']==d['taskName'] and row['updated']['definitionCode']==d['definitionCode'],'restoredBusinessFields':normalized(r.payload(d))==normalized(r.payload(row['restored']))})
finally:
 for c in fixture:m.sql(f"update {SC}.device_capabilities set capability_status={m.lit(c['capability_status'])} where id={c['id']}")
 row['restoredOriginalCapabilities']=m.rows(f"select id,capability_status from {SC}.device_capabilities where id in ({','.join(str(c['id']) for c in fixture)}) order by id");q.cleanup();q.ev['endedAt']=m.now();q.save()
