"""Independent current-version counterexamples, legal controls and own-schema failure.
No product edits. Trigger applies only to explicitly marked GPT tasks/new versions,
is always dropped, and never affects shared schemas/services or other tasks.
"""
import os,importlib.util,json,time,subprocess
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='extra'
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('probe-f019-v168-round.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m
def replay():
 h.reset();row=q.submit('leading-condition-replay',[h.st(),h.st(2),h.st(3),h.st(4)]);h.cfgcase(row,replanSteps=r.condition_tail(3));d,msg=r.prefix(row,2);h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);r.capture(row,'beforeReplay');retry=next(mm for dd,mm in h.msgs(row,'EXECUTE_CAPABILITY') if dd==b and mm['commandId']==cmd['commandId'] and mm['attemptNo']==1);h.feed(row,b,retry,'FAILED','ERR_SYNTHETIC_HARDWARE');h.finish(row);o=r.capture(row);calls=[x for x in r.model_rows(row) if x['phase']=='planning' and any('仅替换步骤' in c for c in x['request'].get('constraints',[]))];row['modelObservations']=calls
 q.record(row,{'http200':all(f['response']['http']==200 for f in row['feedbacks']),'oneCallDespiteReplay':len(calls)==1,'replanPersisted':o['task']['replanUsed'] and len(o['plans'])==2,'completed':o['task']['status']=='COMPLETED','resumedAt4':any(a['plan_version_id']==o['plans'][-1]['id'] and a['step_seq']==4 and a['command_id'] for a in o['allAssignments']),'fivePhysicalSuccesses':sum(c['command_type']=='EXECUTE_CAPABILITY' and c['command_status']=='SUCCEEDED' for c in o['commandRows'])==5})
def scoped_fault(enable):
 assert m.SC=='tip_gpt_f006_v118_20261030'
 if not enable:
  m.sql(f'DROP TRIGGER IF EXISTS gpt_f168_startup_fault ON {m.SC}.task_step_assignments; DROP FUNCTION IF EXISTS {m.SC}.gpt_f168_startup_fault()');return
 m.sql(f"""CREATE FUNCTION {m.SC}.gpt_f168_startup_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF EXISTS (SELECT 1 FROM {m.SC}.tasks t JOIN {m.SC}.plan_versions p ON p.id=NEW.plan_version_id WHERE t.id=NEW.task_id AND ((t.task_goal LIKE 'F168_STARTUP_FAULT %' AND p.version_no=2) OR (t.task_goal LIKE 'F168_BASE_STARTUP_FAULT %' AND p.version_no=3))) THEN RAISE EXCEPTION 'GPT_SYNTHETIC_OWN_SCHEMA_STARTUP_FAILURE'; END IF;
 RETURN NEW; END; $$; CREATE TRIGGER gpt_f168_startup_fault BEFORE INSERT ON {m.SC}.task_step_assignments FOR EACH ROW EXECUTE FUNCTION {m.SC}.gpt_f168_startup_fault()""")
def startup_fault(baseline=False):
 h.reset();name='base-startup-fault' if baseline else 'startup-fault';row=q.submit(name,[h.st(),h.st(2),h.st(3),h.st(4)]);h.cfgcase(row,replanSteps=[h.st(i) for i in [1,2,3]],**({'replanConfidence':.79,'replanDiverse':True} if baseline else {}));d,msg=r.prefix(row,2);scoped_fault(True)
 try:
  h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);r.capture(row,'afterFirstStartupFailure');retry=next(mm for dd,mm in h.msgs(row,'EXECUTE_CAPABILITY') if dd==b and mm['commandId']==cmd['commandId'] and mm['attemptNo']==1);h.feed(row,b,retry,'FAILED','ERR_SYNTHETIC_HARDWARE');o=r.capture(row);calls=[x for x in r.model_rows(row) if x['phase']=='planning' and any('仅替换步骤' in c for c in x['request'].get('constraints',[]))];row['modelObservations']=calls;row['faultScope']='Only own schema task marker/current candidate version assignment INSERT; injected before device dispatch, trigger removed in finally.'
  q.record(row,{'controlledFailureDoesNot500':all(f['response']['http']==200 for f in row['feedbacks']),'consumedQuotaPersists':o['task']['replanUsed'],'snapshotAndVersionPersist':len(o['snapshots'])>len(row['prefix']['snapshots']) and len(o['plans'])>=2,'failureAndManualPersist':o['task']['status']=='PENDING_MANUAL' and bool(h.event(o,'REPLAN_FAILED')) and bool(h.event(o,'TASK_PENDING_MANUAL')),'noRepeatModelCall':len(calls)==1,'prefixPreserved':all(any(a['id']==old['id'] and a==old for a in o['allAssignments']) for old in row['prefix']['allAssignments'] if old['step_status']=='COMPLETED')})
 finally:scoped_fault(False)
def no_retry_truth():
 h.reset();q.devices[1].configure(online='OFFLINE');row=q.submit('no-retry-timeout-truth',[h.st(),h.st(2,timeout=30),h.st(3)]);h.cfgcase(row,replanHttpStatus=503);d,msg=r.prefix(row,1);h.wait(lambda:q.op(f'/tasks/{row["taskId"]}')['status']=='PENDING_MANUAL',48);o=r.capture(row);code=o['task']['taskCode'];proc=subprocess.run(['node',str(r.R/'acceptance/stage3/retest-f019-v168-ui.cjs'),'truth',code],capture_output=True,encoding='utf8',timeout=120);row['ui']={'exit':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr};ui=json.loads((r.R/'acceptance/stage3/evidence/SRS_F019-V1.168-ui-truth-20261106.json').read_text(encoding='utf8'));v=next(v for v in ui['views'] if 'compareText' in v);row['compareText']=v['compareText'];q.record(row,{'noRetryActuallyDispatched':not h.event(o,'STEP_RETRY_DISPATCHED'),'timeoutAndManual':bool(h.event(o,'STEP_TIMEOUT_DETECTED')) and o['task']['status']=='PENDING_MANUAL','summaryDoesNotInventRetry':'指令重试' not in v['compareText'],'originalGoalRetained':o['task']['taskGoal']==row['request']['taskGoal']})
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 for name,fn in [('normal-three',lambda:r.run_case('normal-three')),('overquota-retest',lambda:r.run_case('overquota-four-retest',tail=[h.st(i) for i in [1,2,3,4]],mode='over')),('branch-overquota-retest',lambda:r.run_case('branch-overquota-retest',tail=r.condition_tail(4),mode='over')),('leading-replay',replay),('high-no-baseline',lambda:r.run_case('high-no-baseline',mode='no-baseline',replanConfidence=.79,replanDiverse=True)),('startup-fault',startup_fault),('no-retry-truth',no_retry_truth)]:h.run(name,fn)
 q.run('baseline-trial',r.baseline_setup)
 h.run('base-startup-fault',lambda:startup_fault(True))
finally:
 scoped_fault(False)
 for t in q.templates:
  try:q.cfg(f'/baseline-templates/{t}/disable','POST')
  except Exception:pass
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
