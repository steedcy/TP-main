# Original DEF003 counterexample under a genuinely normal measurement.
r=q.submit('normal-model-false-missing',goalOverride={'infoComplete':False,'missingInfoQuestions':['请提供行李位置','请提供旅客姓名']});o=q.drive(r,oversize=False);r['checks']={'completed':o['task']['status']=='COMPLETED','guardOverrideEvent':any(e.get('reasonCode')=='INFO_CHECK_OVERRIDE' for e in o['events']),'oneGoalInterpretation':not o['task'].get('missingInfoQuestions'),'onlyMeasurementExecuted':[c['step_seq'] for c in o['commandRows'] if c['command_type']=='EXECUTE_CAPABILITY']==[1]};r['result']='P' if all(r['checks'].values()) else 'F';q.save()
# Configured operator/admin role ordering, retaining explicit authorization boundary.
sysadmin=b.l.API('系统管理员');base={'baggageLocation':'F2_TEST_SERVICE','length':55,'width':40,'height':20,'weight':10,'baggageId':'F183-SYSADMIN-EVENT'}
for name,body,expected in [('sysadmin-valid',base,200),('sysadmin-invalid',{},400),('operator-invalid',{},400)]:
 api=sysadmin if name.startswith('sysadmin') else q.op;response=raw(api,'/tasks/measurement-event',body);tid=(response.get('body',{}).get('data') or {}).get('id')
 if tid:q.tasks.append(tid)
 q.record(name,{'taskId':tid,'response':response},{'expectedHttp':response['http']==expected})
# Privacy leak must also be checked before the model boundary, not only completed
# normal event persistence. Only a fictional sentinel is used.
name='event-private-instructions-oversize';q.config('F183-'+name);r=q.event(name,{**base,'baggageId':'F183-'+name,'length':80,'width':55,'height':35,'weight':35,'handlingInstructions':'旅客姓名=FICTIONAL_F183_MODEL_CANARY'});o=q.drive(r);r['after']=o
journal=(L/'f024-v183-model-requests.jsonl').read_text(encoding='utf8');r['checks']={'identityRejectedBeforeModel':r['response']['http']==400,'canaryNotPersisted':'FICTIONAL_F183_MODEL_CANARY' not in json.dumps(o,ensure_ascii=False),'canaryNotSentToModel':'FICTIONAL_F183_MODEL_CANARY' not in journal};r['result']='P' if all(r['checks'].values()) else 'F';q.save();q.terminate(r['taskId'])
# Journal rows and SQL snapshots preserve the existing version/model call facts.
q.ev['modelJournalSummary']={'entries':len(journal.splitlines()),'path':'acceptance/stage3/evidence/SRS_F024-V1.183-model-journal-20261108.jsonl'};q.save();result={'state':q.state()}
