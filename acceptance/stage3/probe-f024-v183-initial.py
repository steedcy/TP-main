"""Executed by the owned fixture control. Full raw requests/responses stay in round JSON."""
base={'baggageLocation':'F2_TEST_SERVICE','baggageId':'F183-EVENT-NORMAL','length':55,'width':40,'height':20,'weight':10,'dimensionThresholdCm':158,'weightThresholdKg':32,'thresholdSource':'SYNTHETIC_DEPLOYMENT_F024_158CM_32KG'}
# Event normal requires no model/plan, first stable health/HTTP/DB gate.
r=q.event('event-normal-explicit32',base)
if r['taskId']:
 o=q.observe(r['taskId']);r['after']=o;r['checks']={'http200':r['response']['http']==200,'completed':o['task']['status']=='COMPLETED','noPlans':len(o['plans'])==0,'noCommands':len(o['commandRows'])==0,'noAssignments':len(o['assignments'])==0,'measurementStored':all(k in o['task']['sceneParams'] for k in ['length','width','height','weight','isOversize','thresholdSource'])};r['result']='P' if all(r['checks'].values()) else 'F';q.save()
result={'normal':r,'state':q.state()}
