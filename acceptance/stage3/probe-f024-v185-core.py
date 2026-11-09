"""Normal/oversize autonomous actual sequential callbacks, false model questions."""
for name,normal,scene,kwargs in [('goal-oversize-four-channel',False,{},{}),('goal-normal-no-guide',True,{},{}),('goal-model-false-missing',False,{}, {'goalOverride':{'infoComplete':False,'missingInfoQuestions':['请提供行李所在位置','请提供旅客姓名']}}),('goal-optional-counter-missing',False,{'targetCounter':None},{})]:
 r=q.submit(name,scene,**kwargs);o=q.drive(r,oversize=not normal);plans=o['plans'];execs=[c for c in o['commandRows'] if c['command_type']=='EXECUTE_CAPABILITY'];p=plans[0] if plans else {};steps=p.get('planSteps',[])
 checks={'http200':r['response']['http']==200,'completed':o['task']['status']=='COMPLETED','oneAutonomousFrozenPlan':len(plans)==1 and p.get('source')=='AUTONOMOUS' and bool(p.get('frozenAt')),'threeChecksPass':all(p.get(k)=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'fiveStepLimit':len(steps)<=5,'feedback200':all(a['response']['http']==200 for a in r.get('actions',[]))}
 if normal:
  checks.update(noGuidePlanGenerated=not any(s.get('capabilityType')=='CAP_NAVIGATION' for s in steps),noFollowupCommands=[c['step_seq'] for c in execs]==[1],remainingSkipped=all(a['stepStatus']=='SKIPPED' for a in o['assignments'] if a['stepSeq']>1))
 else:
  checks.update(fourChannelOrder=[c['step_seq'] for c in execs]==[1,2,3,4],closedLoopEvent=any(e['eventType']=='TASK_COMPLETED' and e.get('reasonCode')=='OVERSIZE_HANDLING_CLOSED_LOOP' for e in o['events']),correctDeviceTypes=all(('SCAN' in a['deviceCode'] if a['message'].get('capabilityType') in ['CAP_BAGGAGE_MEASURE','CAP_OVERSIZE_ALERT'] else ('DISPLAY' in a['deviceCode'] if a['message'].get('capabilityType')=='CAP_INFO_DISPLAY' else 'F016' in a['deviceCode'])) for a in r.get('actions',[]) if a['message']['commandType']=='EXECUTE_CAPABILITY'))
 r['checks']=checks;r['result']='P' if all(checks.values()) else 'F';q.save()
 if o['task']['status']!='COMPLETED':q.terminate(r['taskId'])
result={'state':q.state()}
