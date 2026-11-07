"""Only missing assertions/branches after retained probe diagnostics.
Original same-version sufficient observations are re-evaluated, never re-run.
Run after first-round adapters exit. No product source changes.
"""
import os,importlib.util,json,copy,time,urllib.request,urllib.error
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='supplement'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f021-v173-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;m=r.m;h=r.h;SC=r.SC
original=json.loads((P/'evidence/SRS_F021-V1.173-http-20261107.json').read_text(encoding='utf8'))
q.ev['sourceEvidence']='SRS_F021-V1.173-http-20261107.json';q.ev['corrections']=[]

def saved(name):return next(x for x in original['cases'] if x['name']==name)
def reassess(name,checks,reason):
 source=saved(name);row={'name':'reassess-'+name,'taskId':source['taskId'],'sameObservation':True,'source':q.ev['sourceEvidence'],'reason':reason,'originalResult':source.get('result'),'checks':checks};q.ev['corrections'].append(row);q.save();print(row['name'],checks,flush=True)
def raw_assertions():
 c=saved('exact-200-reason');reassess(c['name'],{'exact200Accepted':c['terminationRequests'][0]['response']['http']==200,'actual200Persisted':c['after']['task']['manualTerminateReason']=='界'*200 and r.detail(c['after']).get('reason')=='界'*200},'operation_logs.detail already parsed to dict by JSON transport; no product deviation')
 c=saved('legal-state-PLANNING');reassess(c['name'],{'legal200':c['terminationRequests'][0]['response']['http']==200,'previousStatusAudited':r.detail(c['after']).get('previousStatus')=='PLANNING'},'same dict parser correction; existing adequate observation reused')
 c=saved('completed-prefix-executing-terminate');before=c['after'];after=c['afterGates'];acts={x['action']:x['response'] for x in c['terminalActions']}
 checks={k:v for k,v in c['checks'].items() if k not in ['terminalActions409','noGateBusinessMutation']}
 checks.update(threeValidManualActions409=all(acts[x]['http']==409 for x in ['RETRY_PLANNING','SWITCH_TO_BASELINE','MARK_FAILED']),forbiddenBypass4004110=all(acts[x]['http']==400 and acts[x]['body']['code']==4110 for x in ['FORCE_RELEASE','REQUEST_SUPERVISION']),taskPlansAssignmentsCommandsUnchanged=all(before[k]==after[k] for k in ['task','plans','assignments','commandRows']),onlyExpectedBypassEventsAppended=[e['eventType'] for e in after['events'][len(before['events']):]]==['FORCE_BYPASS_INTERCEPTED','FORCE_BYPASS_INTERCEPTED'])
 reassess(c['name'],checks,'Existing F013 forbidden-bypass rule requires400/4110 and append-only denial audit/events. Wrong probe blanket409/no-event assertion corrected; original F retained as probe diagnostic.')
 row={'name':'structured-event-operation-audit-original-counterexample','taskId':c['taskId'],'evidence':after};q.ev['cases'].append(row)
 r.record(row,{'operationDetailValidObject':bool(r.detail(after).get('deviceCancelResults')),'eventDetailWholeJSON':r.event_json(after) is not None})

def missing_statuses():
 for status in ['SUPERVISING','PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING','PENDING_MANUAL']:
  row=r.fixture('missing-legal-state-'+status,status);ret=r.term(row);o=r.capture(row);r.record(row,{'legal200':ret['http']==200,'terminal':o['task']['status']=='MANUAL_TERMINATED','previousStatusAudited':r.detail(o).get('previousStatus')==status})
 for status in ['COMPLETED','FAILED','MANUAL_TERMINATED']:
  row=r.fixture('terminal-state-'+status,status);before=r.capture(row,'before');ret=r.term(row);o=r.capture(row);r.record(row,{'terminal409':ret['http']==409,'snapshotUnchanged':r.stable(before)==r.stable(o)})

def cross_task():
 first=r.new('cross-owner-pending-termination',[h.st(timeout=600)]);a,accept1=q.wait_message(first)
 second=q.submit('cross-owner-executing-control',[h.st(timeout=600)]);d,msg=h.accept(second);first['fixtureLevel']='Both naturally selected same available candidate before acceptance; second accepted and executes. First preselection must not revoke second owner.'
 if d!=a:raise RuntimeError('fixture failed to select same candidate; no product verdict')
 before=r.capture(second,'beforeOtherTermination');r.term(first);mid=r.capture(second,'afterOtherTermination');ended=r.capture(first)
 h.feed(second,d,msg);final=r.capture(second)
 r.record(first,{'ownStepsFrozen':all(x['stepStatus']=='FROZEN' for x in ended['assignments']),'otherOwnerRetained':any(x['current_task_id']==second['taskId'] for x in mid['agentRows']),'otherCommandsUnchanged':before['commandRows']==mid['commandRows'],'noCrossTaskCancel':not r.cancels(ended) and not r.cancels(mid),'otherTaskCompletes':final['task']['status']=='COMPLETED'})
 r.record(second,{'controlCompleted':final['task']['status']=='COMPLETED'})

def authorization():
 row=r.fixture('authorization-order-controls','PENDING_MANUAL');before=r.capture(row,'before');row['requests']=[]
 for body in [{},{'reason':'F173 auth control','confirmed':True}]:row['requests'].append({'role':'CONFIG_ADMIN','response':r.raw(row['taskId'],body,api=q.cfg)})
 req=urllib.request.Request(m.l.BASE+f"/tasks/{row['taskId']}/terminate",data=b'{}',headers={'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=10) as res:unauth={'http':res.status,'body':json.load(res)}
 except urllib.error.HTTPError as e:unauth={'http':e.code,'body':json.load(e)}
 row['anonymous']=unauth;o=r.capture(row);r.record(row,{'configRoleBoth403':all(x['response']['http']==403 for x in row['requests']),'anonymous401':unauth['http']==401,'businessUnchanged':all(before[k]==o[k] for k in ['task','plans','assignments','commandRows'])})

def main():
 try:
  raw_assertions();q.setup()
  for fn in [missing_statuses,r.multiple_devices,r.offline_delivery,cross_task,authorization]:q.run(fn.__name__,fn)
 finally:q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
