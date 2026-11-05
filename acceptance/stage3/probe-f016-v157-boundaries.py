"""Remaining independent boundary cases. SQL mutation is limited to owned fixtures.
API capability disable triggers recovery immediately; boundary SQL instead models
loss of eligibility before the next step's assignment without injecting another
business operation. It is explicitly not a production capability-disable test.
"""
import importlib.util,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('f016',Path(__file__).with_name('probe-f016-v157.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.OUT=ROOT/'acceptance/stage3/evidence/SRS_F016-V1.157-boundaries-20261105.json'
q=m.Probe();q.setup();before=q.cfg('/risk-rules');q.ev['rulesBefore']=before
q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
try:
 def gap():
  q.reset();row=q.submit('true-no-candidate-after-first',[m.p.step(seq=1),m.p.step(seq=2)]);d,msg=q.wait_message(row);q.response(d,msg);q.wait_message(row,'EXECUTE_CAPABILITY',d)
  row['fixtureBefore']=q.observe(row['taskId'])
  codes=','.join(m.lit(d.code) for d in q.devices)
  row['fixtureMutation']='Owned device capability_status -> DISABLED without invoking lifecycle; emulate empty candidate set at next-step boundary'
  m.sql(f"update {m.SC}.device_capabilities set capability_status='DISABLED' where capability_code='CAP_NAVIGATION' and device_id in (select id from {m.SC}.devices where device_code in ({codes}))")
  row['feedback']=q.complete(row,d);row['after']=q.observe(row['taskId']);o=row['after']
  q.record(row,{'capabilityGap':any(e['exception_type']=='CAPABILITY_GAP' and e['step_seq']==2 for e in o['exceptions']),'rightReason':any(e.get('reasonCode')=='ERR_NO_CANDIDATE_AVAILABLE' for e in o['events']),'noStepTwoCommand':not any(c['step_seq']==2 for c in o['commandRows']),'pendingManual':o['task']['status']=='PENDING_MANUAL','noCandidateRetry':all(e['recovery_action']=='无可用候选设备，恢复动作未执行' for e in o['exceptions'])})
 q.run('true-no-candidate',gap)
 def disabled_device():
  q.reset();a,b,c=q.devices;c.configure(match=2)
  m.sql(f"update {m.SC}.devices set device_status='INACTIVE' where device_code={m.lit(c.code)}")
  row=q.submit('inactive-device-decoy');d,msg=q.wait_message(row);row['before']=q.observe(row['taskId']);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'inactiveDeviceExcluded':d.agent!=c.agent,'completed':row['after']['task']['status']=='COMPLETED'})
  m.sql(f"update {m.SC}.devices set device_status='ACTIVE' where device_code={m.lit(c.code)}")
 q.run('inactive-device',disabled_device)
 def late():
  q.reset();row=q.submit('late-accept-after-terminate');d,msg=q.wait_message(row);row['before']=q.observe(row['taskId']);row['termination']=m.p.raw(q.op,f'/tasks/{row["taskId"]}/terminate',{'reason':'Synthetic late response','confirmed':True});row['lateResponse']=q.response(d,msg);time.sleep(.15);row['after']=q.observe(row['taskId']);q.record(row,{'terminated':row['after']['task']['status']=='MANUAL_TERMINATED','frozen':all(a['stepStatus']=='FROZEN' for a in row['after']['assignments']),'lateIgnored':any(e['eventType']=='LATE_TASK_RESPONSE_IGNORED' for e in row['after']['events']),'noBusinessTransport':not any(c['message']['commandType']=='EXECUTE_CAPABILITY' for c in d.messages_for(row['after']['task']['taskCode']))});d.configure(work='IDLE')
 q.run('late-frozen-response',late)
finally:
 for r in before:
  if r['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':r['enabled']})
 q.ev['rulesAfter']=q.cfg('/risk-rules');q.cleanup();q.ev['endedAt']=m.now();q.save()
