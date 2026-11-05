"""Supplement missing branches and correct command-selection diagnostics. Fixed product V1.166."""
import os,importlib.util,json,time,subprocess
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='supplement'
R=Path(__file__).resolve().parents[2];s=importlib.util.spec_from_file_location('h',Path(__file__).with_name('probe-f018-v166-helpers.py'));h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
q=h.q;m=h.m

def offline_no_candidate():
 h.reset();q.devices[1].configure(online='OFFLINE');row=q.submit('offline-no-candidate',[h.st(),h.st(2)]);h.cfgcase(row,replanHttpStatus=503);d,msg=h.prefix(row);d.paused=True;h.wait(lambda:q.op(f'/tasks/{row["taskId"]}')['status']=='PENDING_MANUAL',30);o=h.obs(row);q.record(row,{'offlineType':any(e['exception_type']=='AGENT_OFFLINE' for e in o['exceptions']),'prefixPreserved':h.intact(row,o),'oneReplanThenManual':o['task']['replanUsed'] and len(h.event(o,'REPLANNING_TRIGGERED'))==1,'noFalseRecovered':not h.event(o,'EXCEPTION_RECOVERED')})
def baseline(recover):
 h.reset();body={'templateName':'G166 F018 baseline '+str(time.time_ns()),'templateIntent':q.family,'inputParams':q.definitionBody['sceneParams'],'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':180,'completionCondition':'routeGenerated=true'}]};t=q.cfg('/baseline-templates','POST',body);q.templates.append(t['id']);q.save();res=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':q.devices[0].agent}]});trial={'name':'baseline-trial-'+str(recover),'taskId':res['taskId']};q.tasks.append(trial['taskId']);q.ev['cases'].append(trial);d,msg=h.accept(trial);h.feed(trial,d,msg);o=h.obs(trial);q.record(trial,{'realTrialCompleted':o['task']['status']=='COMPLETED'});q.cfg(f"/baseline-templates/{t['id']}/enable",'POST')
 h.reset();row=q.submit('baseline-recovered' if recover else 'baseline-exhausted',high=True);d,msg=h.accept(row);h.failtwice(row,d,msg);mid=h.obs(row,'recovering');d2,msg2=h.accept(row)
 if recover:h.feed(row,d2,msg2)
 else:h.failtwice(row,d2,msg2)
 o=h.obs(row);q.record(row,{'baselineOnly':len(o['plans'])==2 and sum(v['source']=='BASELINE_TEMPLATE' for v in o['plans'])==1,'noReplan':not o['task']['replanUsed'] and not h.event(o,'REPLANNING_TRIGGERED'),'noPrematureSuccess':all(e['recovery_result'] is None and e['exception_status']=='PROCESSING' for e in mid['exceptions']),'rightOutcome':o['task']['status']==('COMPLETED' if recover else 'PENDING_MANUAL'),'finalResults':all(e['exception_status']=='RESOLVED' and e['recovery_result']==('SUCCESS' if recover else 'FAILED') for e in o['exceptions']),'noFalseRecovered':recover or not h.event(o,'EXCEPTION_RECOVERED'),'candidateFinalActionTruth':not recover or (bool(h.event(o,'EXCEPTION_RECOVERED')) and all('候选设备切换' in e['detailSummary'] and '重试成功' not in e['detailSummary'] for e in h.event(o,'EXCEPTION_RECOVERED')))});q.cfg(f"/baseline-templates/{t['id']}/disable",'POST')
def pending_and_ui():
 h.reset();row=q.submit('processing-count-ui',[h.st(),h.st(2),h.st(3)]);d,msg=h.prefix(row);h.failtwice(row,d,msg);o=h.obs(row,'processing');row['overviewBefore']=q.op('/dashboard/overview');row['countsBefore']=m.rows(f"select exception_status,count(*) n from {m.SC}.task_exceptions e join {m.SC}.tasks t on t.id=e.task_id where not t.is_dry_run group by exception_status");n=sum(int(x['n']) for x in row['countsBefore'] if x['exception_status'] in ['PENDING','PROCESSING']);row['expectedUnhandledIncludingProcessing']=n
 q.record(row,{'processingException':any(e['exception_status']=='PROCESSING' for e in o['exceptions']),'unhandledCountIncludesProcessing':row['overviewBefore']['metrics']['unhandledExceptions']==n,'firstRecoveryActionPreserved':all(e['recovery_action']=='指令重试' for e in o['exceptions'])})
 # UI filter fixtures are explicit synthetic DB rows, not production transition evidence.
 row['syntheticStatusFixtureIds']=m.sql(f"insert into {m.SC}.task_exceptions(task_id,step_seq,exception_type,reason_code,exception_status,recovery_action,impact_conclusion) values ({row['taskId']},2,'CAPABILITY_GAP','SYNTHETIC_UI_PENDING','PENDING','UI fixture only','Synthetic status filter sample'),({row['taskId']},2,'STEP_FAILED','SYNTHETIC_UI_IGNORED','IGNORED','UI fixture only','Synthetic status filter sample') returning id").splitlines();q.save()
 proc=subprocess.run(['node',str(R/'acceptance/stage3/retest-f018-v166-ui.cjs'),str(row['taskId']),'catalog'],cwd=R,capture_output=True,encoding='utf-8',timeout=180);row['ui']={'exit':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr};q.save()
 d2,msg2=h.accept(row);h.feed(row,d2,msg2);h.finish(row)
 ids=[x for x in row['syntheticStatusFixtureIds'] if x.isdigit()]
 if ids:m.sql(f"update {m.SC}.task_exceptions set exception_status='RESOLVED',resolved_at=localtimestamp,resolved_by='GPT_UI_FIXTURE_CLEANUP' where id in ({','.join(ids)})")
 row['after']=q.observe(row['taskId']);row['overviewAfter']=q.op('/dashboard/overview');row['unhandledAfter']=q.op('/task-exceptions/pending-count');q.save()
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False});q.ev['settingsBefore']=q.cfg('/settings/heartbeat-timeout');q.cfg('/settings/heartbeat-timeout','PUT',{'seconds':10})
 for name,fn in [('offline-no-candidate',offline_no_candidate),('baseline-recovered',lambda:baseline(True)),('baseline-exhausted',lambda:baseline(False)),('processing-ui',pending_and_ui)]:h.run(name,fn)
finally:
 for t in q.templates:
  try:q.cfg(f'/baseline-templates/{t}/disable','POST')
  except:pass
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 if q.ev.get('settingsBefore'):q.cfg('/settings/heartbeat-timeout','PUT',{'seconds':q.ev['settingsBefore']['seconds']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
