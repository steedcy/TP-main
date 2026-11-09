"""Remaining scalar/alias/default/classification and measurement-result guards."""
base={'baggageLocation':'F2_TEST_SERVICE','length':55,'width':40,'height':20,'weight':10}
def summary(r,checks):r['checks']=checks;r['result']='P' if all(checks.values()) else 'F';q.save()
for name,changes,expected in [('default-weight23-boundary',{'weight':23},False),('default-weight23-plus',{'weight':23.001},True),('small-positive-values',{'length':.001,'width':.001,'height':.001,'weight':.001},False),('event-alias-oversize',{'length':80,'width':55,'height':35,'weight':35},True)]:
 body={**base,'baggageId':'F185-'+name,**changes};q.config('F185-'+name);r=q.event(name,body,path='/tasks/baggage-measurement-event' if 'alias' in name else '/tasks/measurement-event');o=q.observe(r['taskId']);r['before']=o;sp=o['task']['sceneParams'];checks={'http200':r['response']['http']==200,'classificationMatchesDeclaredDefault23':sp.get('isOversize')==expected,'default23':sp.get('weightThresholdKg')==23,'default158':sp.get('dimensionThresholdCm')==158}
 if 'alias' in name:o=q.drive(r);checks['aliasCompletesFourChannels']=o['task']['status']=='COMPLETED'
 summary(r,checks);q.terminate(r['taskId'])
for name,body in [('counter-unconfigured',{**base,'targetCounter':'F185_NONEXISTENT_COUNTER'}),('counter-wrong-type',{**base,'targetCounter':{'invalid':'object'}}),('position-wrong-type',{**base,'baggageLocation':[]}),('threshold-wrong-type',{**base,'weightThresholdKg':'not-a-number'})]:
 before=sql(f'select count(*) from {SC}.tasks');r=q.event(name,body);checks={'invalidRejected':r['response']['http']==400,'noTask':before==sql(f'select count(*) from {SC}.tasks')};summary(r,checks)
 if r.get('taskId'):r['after']=q.observe(r['taskId']);q.save();q.terminate(r['taskId'])
for name,output in [('measurement-missing-dimensions',{'measureStatus':'SUCCESS','weight':10,'isOversize':False}),('measurement-missing-weight',{'measureStatus':'SUCCESS','length':55,'width':40,'height':20,'isOversize':False}),('measurement-missing-oversize',{'measureStatus':'SUCCESS','length':55,'width':40,'height':20,'weight':10})]:
 r=q.submit(name);tid=r['taskId'];code=q.op(f'/tasks/{tid}')['taskCode'];found=[]
 for _ in range(100):
  found=[(d,e['message']) for d in q.devices for e in d.messages_for(code,'TASK_ACCEPT')]
  if found:break
  time.sleep(.1)
 assert found;d,accept=found[-1]
 with d.guard:d.state['workStatus']='BUSY';ar=d.report('TASK_RESPONSE',{'commandId':accept['commandId'],'accepted':True})
 messages=[]
 for _ in range(100):
  messages=d.messages_for(code,'EXECUTE_CAPABILITY')
  if messages:break
  time.sleep(.1)
 assert messages;msg=messages[-1]['message'];feedback={'commandId':msg['commandId'],'attemptNo':msg['attemptNo'],'executionResult':'SUCCESS','outputParams':output}
 with d.guard:ret=d.report('EXECUTION_FEEDBACK',feedback);d.state['workStatus']='IDLE'
 o=q.observe(tid);r.update(feedbackRequest=feedback,feedbackResponse=ret,after=o);summary(r,{'incompleteMeasurementCannotComplete':o['task']['status']!='COMPLETED','incompleteStepCannotComplete':not any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments']),'noFollowupBusiness':not any(c['step_seq']>1 and c['command_type']=='EXECUTE_CAPABILITY' for c in o['commandRows'])});q.terminate(tid)
result={'cases':len(q.ev['cases'])}
