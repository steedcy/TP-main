"""Independent full F019 V2.4 round against packaged V1.170; synthetic HTTP model/devices.
Start fixtures/start-f019-v170-jar.py and controlled model first. No product edits.
All outputs append as new files; credentials remain memory/local private configuration.
"""
import importlib.util,json,time,copy,os,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('h',Path(__file__).with_name('probe-f019-v170-helpers.py'));h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
q=h.q;m=h.m

def capture(row,key='after'):
 o=h.obs(row,key);o['snapshots']=q.op(f'/tasks/{row["taskId"]}/context-snapshots')
 o['allAssignments']=m.rows(f"select a.* from {m.SC}.task_step_assignments a where task_id={row['taskId']} order by id")
 q.save();return o

def prefix(row,n):
 for i in range(n):
  d,msg=h.accept(row);h.feed(row,d,msg,output={'routeGenerated':True,'waypointCount':2,'fixturePrefix':i+1})
 capture(row,'prefix');return h.accept(row)

def model_rows(row):
 path=R/'.local-test/f019-v170-model-requests.jsonl'
 return [x for x in [json.loads(l) for l in path.read_text(encoding='utf8').splitlines()] if row['request']['taskGoal'].split()[0] in x.get('request',{}).get('taskGoal','')]

def invariant(row,o,n,expected_calls=1):
 before=row['prefix'];old=before['plans'][0]
 kept=[a for a in before['allAssignments'] if a['step_status']=='COMPLETED']
 current={a['id']:a for a in o['allAssignments']}
 calls=[x for x in model_rows(row) if x['phase']=='planning' and any('仅替换步骤' in c for c in x['request'].get('constraints',[]))]
 row['modelObservations']=calls;q.save()
 return {'originalGoalUnchanged':o['task']['taskGoal']==row['request']['taskGoal'],
 'completedResultsUnchanged':len(kept)==n and all(current[a['id']]==a for a in kept),
 'originalVersionUnchanged':o['plans'][0]==old,
 'oneModelReplan':len(calls)==expected_calls,
 'exactQuotaAndContext':bool(calls) and calls[0]['request']['remainingStepQuota']==5-n and len(calls[0]['request']['completedSteps'])==n,
 'freshPersistedSnapshot':len(o['snapshots'])>len(before['snapshots']) and len({x['snapshotCode'] for x in o['snapshots']})==len(o['snapshots']),
 'replanUsed':o['task']['replanUsed'],
 'singleTrigger':len(h.event(o,'REPLANNING_TRIGGERED'))==1,
 'recoveryBeforeReplan':bool(h.event(o,'EXCEPTION_RECOVERY_FAILED')) and min(e['id'] for e in h.event(o,'EXCEPTION_RECOVERY_FAILED'))<h.event(o,'REPLANNING_TRIGGERED')[0]['id'],
 'noOldFutureDispatch':not any(c['command_id'] in {a[k] for a in o['allAssignments'] if a['plan_version_id']==old['id'] for k in ['command_id','execute_command_id']} and c['step_seq']>n+1 for c in o['commandRows'])}

def exhaust(row,d,msg):
 h.failtwice(row,d,msg);capture(row,'candidateSwitch');b,cmd=h.accept(row);row['oldFailureCommand']=copy.deepcopy(cmd);row['oldFailureDevice']=b.code
 h.failtwice(row,b,cmd);return capture(row,'replanned')

def condition_tail(actions):
 node={'stepSeq':1,'conditionNode':True,'nodeType':'CONDITION','condition':'routeGenerated=true','stepGoal':'判断是否已生成路径'}
 return [node]+[h.st(i+2,branchOf=1,stepGoal='替换分支动作'+str(i+1)) for i in range(actions)]

def run_case(name,n=2,tail=None,mode='success',**model):
 h.reset();row=q.submit(name,[h.st(i+1,stepGoal='原计划动作'+str(i+1)) for i in range(min(5,n+2))]);h.cfgcase(row,replanSteps=tail if tail is not None else [h.st(i+1,stepGoal='新计划动作'+str(i+1)) for i in range(5-n)],**model)
 if name=='normal-three':
  row['initial']=q.observe(row['taskId']);r=subprocess.run(['node',str(R/'acceptance/stage3/retest-f019-v170-ui.cjs'),'initial',row['initial']['task']['taskCode']],capture_output=True,encoding='utf8',timeout=120);row['initialUI']={'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr};q.save()
 d,msg=prefix(row,n);start=time.monotonic();o=exhaust(row,d,msg);row['replanElapsedSeconds']=time.monotonic()-start
 if mode=='timeout':h.wait(lambda:any(x['phase']=='planning' and any('仅替换步骤' in c for c in x['request'].get('constraints',[])) for x in model_rows(row)),10)
 checks=invariant(row,o,n)
 if mode=='success':
  new=o['plans'][-1];steps=new['planSteps'];checks.update(newPlanFrozen=len(o['plans'])==2 and bool(new['frozenAt']),allThreePass=all(new[x]=='PASS' for x in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),lowSupervision=new['riskLevel']=='LOW' and bool(h.event(o,'SUPERVISION_JUDGED')),prefixMerged=len(steps)==5 and all(steps[i]['outputParams']==row['prefix']['allAssignments'][i]['output_params'] for i in range(n)),replacementOnly=all(a['step_seq']>n or (a['step_status']=='COMPLETED' and a['command_id'] is None and a['execute_command_id'] is None) for a in o['allAssignments'] if a['plan_version_id']==new['id']),noExtraRetrySteps=len([a for a in o['allAssignments'] if a['plan_version_id']==o['plans'][0]['id'] and a['step_seq']==n+1])==1)
  if tail and tail[0].get('conditionNode'):checks.update(conditionNotFrozen=all(not x.get('conditionNode') for x in steps),branchConditionPreserved=sum('branchCondition' in x for x in steps)==5-n)
  end=h.finish(row);end=capture(row);checks.update(completed=end['task']['status']=='COMPLETED',physicalActionsAtMostFive=sum(c['command_type']=='EXECUTE_CAPABILITY' and c['command_status']=='SUCCEEDED' for c in end['commandRows'])==5,oneReplanFinal=len(h.event(end,'REPLANNING_TRIGGERED'))==1)
 elif mode=='second-failure':
  d3,m3=h.accept(row);h.failtwice(row,d3,m3);d4,m4=h.accept(row);h.failtwice(row,d4,m4);end=capture(row)
  checks.update(secondFailureManual=end['task']['status']=='PENDING_MANUAL',onlyTwoPlans=len(end['plans'])==2,stillOnlyOneReplanCall=len([x for x in model_rows(row) if x['phase']=='planning' and any('仅替换步骤' in c for c in x['request'].get('constraints',[]))])==1,noSecondTrigger=len(h.event(end,'REPLANNING_TRIGGERED'))==1,reasonAndImpactRecorded=bool(end['task']['failureReason']) and any('机会已用' in e['impact_conclusion'] for e in end['exceptions'] if e['impact_conclusion']),noFalseRecovered=not h.event(end,'EXCEPTION_RECOVERED'))
 elif mode=='high':
  checks.update(highReplan=len(o['plans'])>=2 and o['plans'][1]['riskLevel']=='HIGH',autoDowngrade=bool(h.event(o,'BASELINE_DOWNGRADED')),retainedTwoCompleted=len(o['plans'][-1]['planSteps'])==5 and sum(a['plan_version_id']==o['plans'][-1]['id'] and a['step_seq']<=n and a['step_status']=='COMPLETED' and a['command_id'] is None for a in o['allAssignments'])==n,baselineThreePass=o['plans'][-1]['source']=='BASELINE_TEMPLATE' and all(o['plans'][-1][x]=='PASS' for x in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']))
  end=h.finish(row);end=capture(row);checks.update(completed=end['task']['status']=='COMPLETED',noPrefixRedispatch=sum(c['command_type']=='EXECUTE_CAPABILITY' and c['command_status']=='SUCCEEDED' for c in end['commandRows'])==5)
 else:
  checks.update(manual=o['task']['status']=='PENDING_MANUAL',replanFailedException=any(e['exception_type']=='REPLAN_FAILED' and e['recovery_result']=='FAILED' for e in o['exceptions']),noNewPlanCommands=not any(a['plan_version_id']!=o['plans'][0]['id'] and a['command_id'] is not None for a in o['allAssignments']),noSuccessEvent=not h.event(o,'REPLAN_SUCCEEDED'),preservedCurrentVersion=o['task']['currentPlanVersionId']==o['plans'][0]['id'])
  if mode=='over':checks.update(noTruncation=len(o['plans'])==1 and any(e['reasonCode']=='ERR_STEP_LIMIT_EXCEEDED' for e in h.event(o,'REPLAN_FAILED')))
  if mode in ['structure','capability','constraint']:checks.update(rejectedCandidateRetained=len(o['plans'])==2 and o['plans'][-1][mode+'CheckResult']=='FAIL',notFrozen=not o['plans'][-1].get('frozenAt'))
  if mode=='timeout':checks['actual60SecondTimeout']=59<=row['replanElapsedSeconds']<70
 q.record(row,checks);return row

def baseline_setup():
 h.reset();body={'templateName':'G170 F019 baseline '+str(time.time_ns()),'templateIntent':q.family,'inputParams':q.definitionBody['sceneParams'],'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':180,'completionCondition':'routeGenerated=true'} for i in range(5)]}
 t=q.cfg('/baseline-templates','POST',body);q.templates.append(t['id']);q.save();res=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':i+1,'agentId':q.devices[0].agent} for i in range(5)]});trial={'name':'baseline-trial','taskId':res['taskId']};q.tasks.append(trial['taskId']);q.ev['cases'].append(trial);o=h.finish(trial);capture(trial);q.record(trial,{'realFiveStepTrialCompleted':o['task']['status']=='COMPLETED'});q.cfg(f"/baseline-templates/{t['id']}/enable",'POST');return t

def late_feedback():
 h.reset();row=q.submit('timeout-rollback-and-late-feedback',[h.st(),h.st(2,timeout=30),h.st(3)]);h.cfgcase(row,replanSteps=[h.st()],replanHttpStatus=503);d,msg=prefix(row,1);start=time.monotonic();h.wait(lambda:any(e['eventType']=='STEP_TIMEOUT_DETECTED' for e in q.op(f'/tasks/{row["taskId"]}/events')),48);mid=capture(row,'timedOut');late=h.feed(row,d,msg);row['lateResponse']=late;after=capture(row,'afterLateFeedback');b,cmd=h.accept(row);h.failtwice(row,b,cmd);o=capture(row)
 q.record(row,{'actualTimeoutAt30':time.monotonic()-start>=29,'timeoutRecorded':bool(h.event(mid,'STEP_TIMEOUT_DETECTED')),'lateSuccessIgnored':after['task']['status']!='COMPLETED' and not any(a['stepSeq']==2 and a['stepStatus']=='COMPLETED' for a in after['assignments']),'prefixPreserved':h.intact(row,o),'noOldFutureCommands':not any(c['step_seq']==3 for c in o['commandRows']),'oneReplanManual':o['task']['replanUsed'] and o['task']['status']=='PENDING_MANUAL'})

def main():
 try:
  q.setup();
  for d in q.devices:d.stable_callback_clock=True
  q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
  # Two successful prefix steps, three replacements: formal TC060/061 legal boundary.
  h.run('normal-three',lambda:run_case('normal-three'))
  h.run('conditional-three',lambda:run_case('conditional-three',tail=condition_tail(3)))
  h.run('overquota-four',lambda:run_case('overquota-four',tail=[h.st(i+1) for i in range(4)],mode='over'))
  h.run('branch-overquota-four',lambda:run_case('branch-overquota-four',tail=condition_tail(4),mode='over'))
  h.run('one-remaining',lambda:run_case('one-remaining',n=4))
  h.run('five-remaining',lambda:run_case('five-remaining',n=0))
  h.run('second-failure',lambda:run_case('second-failure',mode='second-failure'))
  for label,kw in [('request-failure',{'replanHttpStatus':500}),('model-unavailable',{'replanHttpStatus':503}),('malformed-model',{'replanMode':'MALFORMED'}),('model-error-code',{'replanResultCode':'ERROR'})]:h.run(label,lambda label=label,kw=kw:run_case(label,mode='model',**kw))
  missing=h.st();missing.pop('stepGoal')
  for label,step in [('structure',missing),('capability',h.st(capabilityType='CAP_F019_NOT_REGISTERED')),('constraint',h.st(inputParams={'targetLocation':'F2_TEST_GATE','waypoint':[1,2]}))]:h.run(label,lambda label=label,step=step:run_case('invalid-'+label,tail=[step],mode=label))
  h.run('empty-tail',lambda:run_case('empty-tail',tail=[],mode='over'))
  h.run('timeout-rollback',late_feedback)
  h.run('model-timeout',lambda:run_case('model-timeout',mode='timeout',replanDelay=65))
  q.run('baseline-setup',baseline_setup)
  h.run('replan-high-risk',lambda:run_case('replan-high-risk',mode='high',replanConfidence=.79,replanDiverse=True))
 finally:
  for t in q.templates:
   try:q.cfg(f'/baseline-templates/{t}/disable','POST')
   except Exception:pass
  for rule in q.ev.get('rulesBefore',[]):
   if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
  q.cleanup();q.ev['endedAt']=m.now();q.save()

if __name__=='__main__':main()
