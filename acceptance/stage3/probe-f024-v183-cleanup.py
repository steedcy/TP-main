q.ev['preCleanupTasks']=rows(f"select id,task_code,status,current_plan_version_id,replan_used from {SC}.tasks where id in ({','.join(map(str,q.tasks))}) order by id")
for tid in q.templates:
 if q.cfg(f'/baseline-templates/{tid}').get('status')=='ENABLED':q.cfg(f'/baseline-templates/{tid}/disable','POST')
q.cleanup()
q.ev['finalRisk']=q.cfg('/risk-rules');q.ev['finalTemplates']=[q.cfg(f'/baseline-templates/{tid}') for tid in q.templates]
q.ev['finalTasks']=rows(f"select id,task_code,status,current_plan_version_id,replan_used from {SC}.tasks where id in ({','.join(map(str,q.tasks))}) order by id")
q.ev['finalDevices']=rows(f"select d.device_code,d.device_status,a.agent_status,a.online_status,a.work_status,a.current_task_id from {SC}.devices d join {SC}.device_agents a on a.device_id=d.id where d.device_code in ({','.join(lit(d.code) for d in q.devices)}) order by d.id")
q.ev['triggers']=rows(f"select trigger_name,event_object_table from information_schema.triggers where trigger_schema={lit(SC)}")
q.ev['configurationRestoration']={'riskEnabledRestored':{r['ruleCode']:r['enabled'] for r in q.ev['riskBefore']}=={r['ruleCode']:r['enabled'] for r in q.ev['finalRisk']},'allRoundTasksTerminal':all(t['status'] in ['COMPLETED','FAILED','MANUAL_TERMINATED'] for t in q.ev['finalTasks']),'allOwnedDevicesInactive':all(d['device_status']=='INACTIVE' for d in q.ev['finalDevices']),'allOwnedDevicesUnoccupied':all(d['current_task_id'] is None for d in q.ev['finalDevices']),'taskDefinitionUnmodified':rows(f"select * from {SC}.task_definitions where definition_code='OVERSIZE_BAGGAGE_HANDLING'")==q.ev['presetBefore'],'triggerCount':len(q.ev['triggers'])}
q.ev['network']=q.net;q.ev['endedAt']=b.now();q.save()
(E/'SRS_F024-V1.183-model-journal-20261108.jsonl').write_text((L/'f024-v183-model-requests.jsonl').read_text(encoding='utf8'),encoding='utf8',newline='\n')
result={'cleanup':q.ev['configurationRestoration'],'lastObservation':q.ev['cases'][-1]['checks'],'tasks':len(q.tasks)}
