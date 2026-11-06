"""Normal owned JAR restart: separate task-code114 from snapshot113 fix.
Bounded retry preserves every response; no database rewrites or shared faults.
"""
import os,importlib.util,json
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='restart'
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('probe-f019-v169-round.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m
try:
 q.setup();q.ev['preRequestTaskCount']=int(m.sql(f'select count(*) from {m.SC}.tasks'));q.ev['preRequestSnapshotCount']=int(m.sql(f'select count(*) from {m.SC}.context_snapshots'));q.ev['preRequestSnapshotMaxSuffix']=int(m.sql(f"select coalesce(max(substring(snapshot_code from '[0-9]+$')::bigint),0) from {m.SC}.context_snapshots where snapshot_code like 'CTX-20261106-%'"));nextTask=f"TASK-20261106-{q.ev['preRequestTaskCount']+1:04d}";q.ev['predictedCountBasedTaskCode']=nextTask;q.ev['preexistingTaskCollisionRows']=m.rows(f"select id,task_code,created_at from {m.SC}.tasks where task_code={m.lit(nextTask)}");q.ev['responses']=[];q.save()
 for attempt in range(1,9):
  marker='F169_RESTART_CAPTURE_'+str(attempt);q.cases[marker]={'steps':[h.st()],'goalCompletion':'routeGenerated=true','confidence':.99};(r.R/'.local-test/f019-v169-cases.json').write_text(json.dumps(q.cases),encoding='utf8');body={'taskGoal':marker+' synthetic navigation to F2_TEST_GATE','taskFamily':q.family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}};res=m.p.raw(q.op,'/tasks',body);item={'attempt':attempt,'request':body,'response':res};q.ev['responses'].append(item);q.save();tid=m.sql(f'select id from {m.SC}.tasks where task_goal={m.lit(body["taskGoal"])} order by id desc limit 1')
  if tid:
   row={'name':'restart-snapshot-creation','taskId':int(tid),'request':body,'response':res};q.tasks.append(row['taskId']);q.ev['cases'].append(row);h.finish(row);o=r.capture(row);codes=[x['snapshotCode'] for x in o['snapshots']];q.record(row,{'acceptedAfterCountAdvances':res['http'] in [200,201],'taskCompleted':o['task']['status']=='COMPLETED','snapshotStored':bool(codes),'snapshotBeyondPreviousMax':all(int(c.rsplit('-',1)[1])>q.ev['preRequestSnapshotMaxSuffix'] for c in codes),'snapshotUnique':all(int(m.sql(f"select count(*) from {m.SC}.context_snapshots where snapshot_code={m.lit(c)}"))==1 for c in codes)});break
 row={'name':'restart-task-create-gate','taskId':None,'request':q.ev['responses'][0]['request'],'response':q.ev['responses'][0]['response']};q.ev['cases'].append(row);q.record(row,{'firstCreateSuccess':row['response']['http'] in [200,201],'nextTaskCodeNotAlreadyUsed':not bool(q.ev['preexistingTaskCollisionRows'])})
finally:q.cleanup();q.ev['endedAt']=m.now();q.save()
