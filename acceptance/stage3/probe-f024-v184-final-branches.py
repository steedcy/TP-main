# Original DEF003 counterexample under a genuinely normal measurement.
r=q.submit('normal-model-false-missing',goalOverride={'infoComplete':False,'missingInfoQuestions':['请提供行李位置','请提供旅客姓名']});o=q.drive(r,oversize=False);r['checks']={'completed':o['task']['status']=='COMPLETED','guardOverrideEvent':any(e.get('reasonCode')=='INFO_CHECK_OVERRIDE' for e in o['events']),'oneGoalInterpretation':not o['task'].get('missingInfoQuestions'),'onlyMeasurementExecuted':[c['step_seq'] for c in o['commandRows'] if c['command_type']=='EXECUTE_CAPABILITY']==[1]};r['result']='P' if all(r['checks'].values()) else 'F';q.save()
# Configured operator/admin role ordering, retaining explicit authorization boundary.
sysadmin=b.l.API('系统管理员');base={'baggageLocation':'F2_TEST_SERVICE','length':55,'width':40,'height':20,'weight':10,'baggageId':'F184-SYSADMIN-EVENT'}
for name,body,expected in [('sysadmin-valid',base,200),('sysadmin-invalid',{},400),('operator-invalid',{},400)]:
 api=sysadmin if name.startswith('sysadmin') else q.op;response=raw(api,'/tasks/measurement-event',body);tid=(response.get('body',{}).get('data') or {}).get('id')
 if tid:q.tasks.append(tid)
 q.record(name,{'taskId':tid,'response':response},{'expectedHttp':response['http']==expected})
# Privacy leak must also be checked before the model boundary, not only completed
# normal event persistence. Only a fictional sentinel is used.
name='event-private-instructions-oversize';q.config('F184-'+name);r=q.event(name,{**base,'baggageId':'F184-'+name,'length':80,'width':55,'height':35,'weight':35,'handlingInstructions':'旅客姓名=FICTIONAL_F184_MODEL_CANARY'})
# A rejected privacy canary has no task id.  The previous probe called drive(None),
# producing a harness HTTP 500 and leaving a null diagnostic row.  Keep that row
# untouched and record this corrected observation without invoking the task driver.
journal=(L/'f024-v184-model-requests.jsonl').read_text(encoding='utf8')
canary='FICTIONAL_F184_MODEL_CANARY';business='F184-event-private-instructions-oversize'
databaseCanaryRows=rows(f"select id,task_code,task_goal,scene_params,goal_parsing_result from {SC}.tasks where task_goal like {lit('%'+canary+'%')} or scene_params::text like {lit('%'+canary+'%')} or goal_parsing_result::text like {lit('%'+canary+'%')}")
databaseEventRows=rows(f"select id,task_id,event_type,detail_summary from {SC}.task_events where detail_summary like {lit('%'+canary+'%')}")
relatedTaskRows=rows(f"select id,task_code,status from {SC}.tasks where scene_params::text like {lit('%'+business+'%')} or task_goal like {lit('%'+business+'%')}")
databaseEvidence={'canaryTaskRows':databaseCanaryRows,'canaryEventRows':databaseEventRows,'relatedTaskRows':relatedTaskRows}
if r.get('taskId'):
    o=q.drive(r);r['after']=o
    no_task=False
    canary_not_persisted=not databaseCanaryRows and not databaseEventRows and canary not in json.dumps(o,ensure_ascii=False)
else:
    o={'task':None,'events':[],'assignments':[],'commands':[],'exceptions':[]}
    r['after']=o
    no_task=not relatedTaskRows
    canary_not_persisted=not databaseCanaryRows and not databaseEventRows
r['databaseEvidence']=databaseEvidence
r['probeCorrection']={'originalNullRowsRetained':True,'reason':'HTTP rejection has no task; skip drive(None)'}
r['checks']={'identityRejectedBeforeModel':r['response']['http']==400,'noTaskCreated':no_task,'canaryNotPersisted':canary_not_persisted,'canaryNotSentToModel':canary not in journal};r['result']='P' if all(r['checks'].values()) else 'F';q.save()
if r.get('taskId'):q.terminate(r['taskId'])
# Journal rows and SQL snapshots preserve the existing version/model call facts.
q.ev['modelJournalSummary']={'entries':len(journal.splitlines()),'path':'acceptance/stage3/evidence/SRS_F024-V1.184-model-journal-20261109.jsonl'};q.save();result={'state':q.state()}
