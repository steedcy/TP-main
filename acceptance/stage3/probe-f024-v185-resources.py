"""Offline/no-candidate branches; only own synthetic devices are changed."""
def record(r,o,checks):r['after']=o;r['checks']=checks;r['result']='P' if all(checks.values()) else 'F';q.save()
for name,typ in [('no-scanner','BAGGAGE_SCANNER'),('no-mobile','MOBILE_ROBOT')]:
 affected=[d for d in q.devices if d.simtype==typ]
 try:
  for d in affected:d.configure(online='OFFLINE')
  r=q.submit(name);o=q.drive(r) if name=='no-mobile' else q.observe(r['taskId']);execs=[c for c in o['commandRows'] if c['command_type']=='EXECUTE_CAPABILITY']
  if name=='no-scanner':checks={'noFakeMeasurement':not execs and not any(a.get('outputParams') for a in o['assignments']),'capabilityGapRecorded':any(x['exception_type']=='CAPABILITY_GAP' for x in o['exceptions']) or any(e.get('reasonCode')=='CAPABILITY_GAP' or 'CAPABILITY_GAP' in str(e.get('detailSummary')) for e in o['events']),'safeManual':o['task']['status']=='PENDING_MANUAL'}
  else:checks={'informationPublished':any(a['message']['commandType']=='EXECUTE_CAPABILITY' and a['message'].get('capabilityType')=='CAP_INFO_DISPLAY' for a in r.get('actions',[])),'measured':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments']),'uncompletedGuidanceMarked':any('未完成引导' in str(e) or '未覆盖' in str(e) for e in o['events']) or '未完成引导' in str(o['task']),'noFalseClosedLoop':not any(e.get('reasonCode')=='OVERSIZE_HANDLING_CLOSED_LOOP' for e in o['events'])}
  record(r,o,checks);q.terminate(r['taskId'])
 finally:
  for d in affected:d.configure()
# Measurement already executing: immediate protocol OFFLINE causes real recovery.
r=q.submit('measurement-device-offline-recovery');tid=r['taskId'];code=q.op(f'/tasks/{tid}')['taskCode'];primary=None
for _ in range(100):
 found=[(d,e['message']) for d in q.devices for e in d.messages_for(code,'TASK_ACCEPT')]
 if found:primary,accept=found[-1];break
 time.sleep(.1)
assert primary is not None
with primary.guard:
 primary.state['workStatus']='BUSY';ret=primary.report('TASK_RESPONSE',{'commandId':accept['commandId'],'accepted':True});primary.configure(online='OFFLINE',work='BUSY')
r['offlineReport']=ret
# Avoid replaying the already accepted primary request; the controlled adapter marks
# old envelopes observed while preserving a copy in r before processing new traffic.
r['preOfflineMessages']=copy.deepcopy(primary.messages_for(code));old=primary.messages;primary.messages=[e for e in old if e['message'].get('taskId')!=code]
try:
 o=q.drive(r);record(r,o,{'recoveryObserved':any(e['eventType'] in ['EXCEPTION_RECOVERED','REPLANNING_TRIGGERED','AGENT_OFFLINE_DETECTED'] or e.get('reasonCode')=='AGENT_OFFLINE' for e in o['events']),'noFalseCompletion':o['task']['status']!='COMPLETED' or all(a['stepStatus'] in ['COMPLETED','SKIPPED'] for a in o['assignments']),'completedWithBackup':o['task']['status']=='COMPLETED'})
finally:
 primary.messages=r['preOfflineMessages']+primary.messages;primary.configure();q.terminate(tid)
result={'state':q.state()}
