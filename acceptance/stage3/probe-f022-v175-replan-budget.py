"""F022 R05 direct dependency: real recovery/replan, five-action global budget.
Independent production JAR/HTTP/synthetic callbacks, not SQL-synthesized lifecycle.
"""
import os,importlib.util,json,copy
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='replan-budget'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f022-v175-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m;SC=r.SC;R=r.R
def run(name,remaining):
 row=r.new(name,[h.st(i+1,timeout=600) for i in range(3)],scene={'targetLocation':'F2_TEST_GATE'},replanSteps=[h.st(i+1,timeout=600) for i in range(remaining)])
 d,msg=h.accept(row);h.feed(row,d,msg);r.capture(row,'completedPrefix');d,msg=h.accept(row);h.failtwice(row,d,msg);r.capture(row,'afterFirstCandidate');backup,cmd=h.accept(row);h.failtwice(row,backup,cmd);o=r.capture(row,'afterReplan')
 if remaining==4:
  end=h.finish(row);done=[a for a in end['assignments'] if a['stepStatus']=='COMPLETED']
  r.record(row,{'realReplanTriggered':any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events']),'completedPrefixRetained':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in end['assignments']),'atLeastTwoVersions':len(end['plans'])>=2,'allVersionsAtMostFive':all(len(p['planSteps'])<=5 for p in end['plans']),'actualPathAtMostFive':len(done)<=5,'completedOrRiskGate':end['task']['status']=='COMPLETED' or (end['task']['status']=='PENDING_MANUAL' and any(e.get('reasonCode')=='RULE_RESOURCE_CRITICAL' for e in end['events']))})
 else:
  r.record(row,{'realReplanTriggered':any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events']),'rejectReason':'ERR_STEP_LIMIT_EXCEEDED' in json.dumps(o) or 'ERR_TOTAL_STEP_LIMIT_EXCEEDED' in json.dumps(o),'noInvalidFrozen':all(not p['frozenAt'] or len(p['planSteps'])<=5 for p in o['plans']),'noTaskCompletion':o['task']['status']!='COMPLETED','prefixRetained':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments'])});q.terminate(row)
def main():
 try:
  q.tasks.append(993);q.terminate({'taskId':993});q.setup()
  for name,n in [('replan-prefix1-plus4-global5',4),('replan-prefix1-plus5-global6-rejected',5)]:q.run(name,lambda name=name,n=n:run(name,n))
 finally:q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
