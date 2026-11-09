"""Event input equivalence/boundary/authorization/privacy groups."""
base={'baggageLocation':'F2_TEST_SERVICE','length':55,'width':40,'height':20,'weight':10,'dimensionThresholdCm':158,'weightThresholdKg':32,'thresholdSource':'SYNTHETIC_DEPLOYMENT_F024_158CM_32KG'}
def finish(r,checks,observe=True):
 if r.get('taskId') and observe:r['after']=q.observe(r['taskId'])
 r['checks']=checks;r['result']='P' if all(checks.values()) else 'F';q.save()
def sample(name,changes,expected,path='/tasks/measurement-event'):
 body={**base,'baggageId':'F184-'+name,**changes};q.config('F184-'+name);r=q.event(name,body,path=path)
 checks={'http200':r['response']['http']==200}
 if r.get('taskId'):
  o=q.observe(r['taskId']);r['before']=o;sp=o['task']['sceneParams'];checks.update(resultCorrect=sp.get('isOversize')==expected,thresholdAndSource=sp.get('dimensionThresholdCm')==body['dimensionThresholdCm'] and sp.get('weightThresholdKg')==body['weightThresholdKg'] and sp.get('thresholdSource')==body['thresholdSource'])
  if expected:
   o=q.drive(r);checks.update(completed=o['task']['status']=='COMPLETED',fourChannelsExecuted=len([c for c in o['commandRows'] if c['command_type']=='EXECUTE_CAPABILITY'])==4)
  else:checks.update(completed=o['task']['status']=='COMPLETED',noPlans=len(o['plans'])==0,noCommands=len(o['commandRows'])==0)
 finish(r,checks)
for name,changes,expected in [('event-dimension-equal',{'length':63,'width':55,'height':40},False),('event-dimension-plus',{'length':63.001,'width':55,'height':40},True),('event-weight-equal',{'weight':32},False),('event-weight-plus',{'weight':32.001},True),('event-optional-counter-empty',{'targetCounter':''},False),('event-optional-counter-spaces',{'targetCounter':'   '},False),('event-counter-explicit',{'targetCounter':'F2_TEST_GATE'},False)]:sample(name,changes,expected)
sample('event-alias-normal',{},False,'/tasks/baggage-measurement-event')
for field,val in [('baggageLocation',''),('baggageLocation','  '),('baggageLocation',None),('length',0),('length',-0.001),('length',None),('width',0),('height',0),('weight',0),('weight',-0.001),('weight',None),('length','not-a-number'),('dimensionThresholdCm',0),('weightThresholdKg',-1)]:
 body={**base,field:val};before=sql(f'select count(*) from {SC}.tasks');r=q.event('event-invalid-'+field+'-'+str(val),body);after=sql(f'select count(*) from {SC}.tasks');finish(r,{'http400':r['response']['http']==400,'noTaskCreated':before==after},False)
 if r.get('taskId'):q.terminate(r['taskId'])
for name,payload in [('top',{'passengerName':'FICTIONAL_F184_PRIVATE_CANARY'}),('nested',{'context':{'ID_CARD':'FICTIONAL_F184_PRIVATE_CANARY'}}),('list',{'context':[{'Phone':'FICTIONAL_F184_PRIVATE_CANARY'}]}),('json',{'context':json.dumps({'passportNumber':'FICTIONAL_F184_PRIVATE_CANARY'})}),('instructions',{'handlingInstructions':'旅客姓名=FICTIONAL_F184_PRIVATE_CANARY'}),('source',{'thresholdSource':'旅客姓名=FICTIONAL_F184_PRIVATE_CANARY'}),('devicecode',{'deviceCode':'旅客姓名=FICTIONAL_F184_PRIVATE_CANARY'})]:
 before=sql(f'select count(*) from {SC}.tasks');r=q.event('event-privacy-'+name,{**base,**payload});after=sql(f'select count(*) from {SC}.tasks');finish(r,{'identityRejected':r['response']['http']==400,'noTaskCreated':before==after})
for name,api in [('anonymous',None),('config-admin',q.cfg)]:
 for valid in [True,False]:
  before=sql(f'select count(*) from {SC}.tasks');response=raw(api,'/tasks/measurement-event',base if valid else {});after=sql(f'select count(*) from {SC}.tasks');q.record('event-authorization-'+name+'-'+str(valid),{'response':response},{'expectedStatus':response['http']==(401 if api is None else 403),'noTask':before==after})
# Explicit false scalar and arbitrary extra map must not replace trusted calculation.
r=q.event('event-extra-computed-override',{**base,'isOversize':True,'extraParams':{'length':999,'weightThresholdKg':0,'tempBusinessId':'F184-OVERRIDE'}})
if r.get('taskId'):
 o=q.observe(r['taskId']);sp=o['task']['sceneParams'];r['after']=o;finish(r,{'consistentNormal':sp.get('isOversize') is False,'lengthMatchesMeasurement':sp.get('length')==55,'thresholdMatchesInput':sp.get('weightThresholdKg')==32})
result={'caseCount':len(q.ev['cases']),'state':q.state()}
