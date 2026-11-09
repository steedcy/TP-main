"""Natural open-goal inference reaches the family-specific required-info guard.
All canaries are fictional; inspect HTTP/DB/events/model journals separately.
"""
marker='F185_OPEN_MISSING_LOCATION';q.config(marker,goalOverride={'inferredTaskFamily':'OVERSIZE_BAGGAGE_HANDLING','infoComplete':False,'missingInfoQuestions':['提供行李位置和旅客姓名']})
body={'taskGoal':marker+' 行李处置','sceneParams':{'tempBusinessId':'F185-CLARIFY','targetLocation':'F2_TEST_GATE'}}
response=raw(q.op,'/tasks',body);data=response.get('body',{}).get('data') or {};tid=data.get('id')
if tid:
 q.tasks.append(tid);r=q.record('genuine-missing-location',{'taskId':tid,'request':body,'response':response,'before':q.observe(tid)});o=r['before'];questions=o['task'].get('missingInfoQuestions') or []
 if isinstance(questions,str):questions=json.loads(questions)
 r['checks']={'onlyLocationQuestion':len(questions)==1 and '位置' in questions[0] and '姓名' not in questions[0],'noPlansOrCommands':not o['plans'] and not o['commandRows']};r['result']='P' if all(r['checks'].values()) else 'F';q.save()
 for name,answers in [('top',{'passengerName':'FICTIONAL_F185_CLARIFY_CANARY'}),('json',{questions[0]:json.dumps({'idCard':'FICTIONAL_F185_CLARIFY_CANARY'})})]:
  before=q.observe(tid);res=raw(q.op,f'/tasks/{tid}/clarify',{'answers':answers});after=q.observe(tid);q.record('clarification-privacy-'+name,{'taskId':tid,'response':res,'before':before,'after':after},{'rejected':res['http']==400,'sceneUnchanged':before['task']['sceneParams']==after['task']['sceneParams'],'noCommands':not after['commandRows']})
 res=raw(q.op,f'/tasks/{tid}/clarify',{'answers':{questions[0]:'F2_TEST_SERVICE'}});o=q.drive(r);q.record('clarification-legal-location-answer',{'taskId':tid,'response':res,'after':o},{'answer200':res['http']==200,'noRepeatFalseQuestion':not o['task'].get('missingInfoQuestions'),'completed':o['task']['status']=='COMPLETED'});q.terminate(tid)
else:q.record('genuine-missing-location',{'request':body,'response':response},{'createdNaturalClarification':False})
for name,sp in [('top',{'passengerName':'FICTIONAL_F185_GOAL_CANARY'}),('nested',{'metadata':{'identityDocumentNumber':'FICTIONAL_F185_GOAL_CANARY'}}),('list',{'metadata':[{'phone':'FICTIONAL_F185_GOAL_CANARY'}]}),('json',{'metadata':json.dumps({'passengerName':'FICTIONAL_F185_GOAL_CANARY'})})]:
 body={'taskGoal':'F185_PRIVACY_GOAL_'+name,'taskFamily':'OVERSIZE_BAGGAGE_HANDLING','sceneParams':{'baggageLocation':'F2_TEST_SERVICE',**sp}};before=sql(f'select count(*) from {SC}.tasks');res=raw(q.op,'/tasks',body);q.record('goal-privacy-'+name,{'request':body,'response':res},{'http400':res['http']==400,'noTaskCreated':before==sql(f'select count(*) from {SC}.tasks')})
result={'state':q.state()}
