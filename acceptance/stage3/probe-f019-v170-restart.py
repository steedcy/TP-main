"""Actual packaged-JAR normal restart, retained historical gaps, common allocator."""
import os,importlib.util,json
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='restart'
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('probe-f019-v170-round.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m
def maxsuffix(table,col,prefix):return int(m.sql(f"select coalesce(max(substring({col} from '[0-9]+$')::bigint),0) from {m.SC}.{table} where {col} like '{prefix}20261106-%'"))
try:
 q.setup();q.ev['preRequestTaskCount']=int(m.sql(f'select count(*) from {m.SC}.tasks'));q.ev['preRequestTaskMaxSuffix']=maxsuffix('tasks','task_code','TASK-');q.ev['preRequestSnapshotMaxSuffix']=maxsuffix('context_snapshots','snapshot_code','CTX-');nextTask=f"TASK-20261106-{q.ev['preRequestTaskCount']+1:04d}";q.ev['predictedOldCountBasedCode']=nextTask;q.ev['oldCountCollisionRows']=m.rows(f"select id,task_code from {m.SC}.tasks where task_code={m.lit(nextTask)}");q.save()
 def create(name):
  row=q.submit(name,[h.st()]);h.finish(row);o=r.capture(row);code=o['task']['taskCode'];codes=[x['snapshotCode'] for x in o['snapshots']]
  q.record(row,{'firstHttpSuccess':row['response']['http']==200,'completed':o['task']['status']=='COMPLETED','codeBeyondPreRestartMax':int(code.rsplit('-',1)[1])>q.ev['preRequestTaskMaxSuffix'],'taskCodeUnique':int(m.sql(f"select count(*) from {m.SC}.tasks where task_code={m.lit(code)}"))==1,'snapshotBeyondPreRestartMax':bool(codes) and all(int(c.rsplit('-',1)[1])>q.ev['preRequestSnapshotMaxSuffix'] for c in codes),'snapshotUnique':all(int(m.sql(f"select count(*) from {m.SC}.context_snapshots where snapshot_code={m.lit(c)}"))==1 for c in codes)})
 h.run('restart-first-create',lambda:create('restart-first-create'))
 q.run('restart-baseline-trial',r.baseline_setup)
 h.run('restart-following-create',lambda:create('restart-following-create'))
 allrows=m.rows(f"select id,task_code from {m.SC}.tasks where id in ({','.join(map(str,q.tasks))}) order by id")
 row={'name':'restart-shared-generator','taskId':None,'allocated':allrows};q.ev['cases'].append(row);seq=[int(x['task_code'].rsplit('-',1)[1]) for x in allrows];q.record(row,{'threePersistedAcrossOrdinaryAndTrial':len(seq)==3,'strictlyIncreasing':seq==sorted(set(seq)),'allBeyondPreRestartMax':all(x>q.ev['preRequestTaskMaxSuffix'] for x in seq)})
finally:
 for t in q.templates:
  try:q.cfg(f'/baseline-templates/{t}/disable','POST')
  except Exception:pass
 q.cleanup();q.ev['endedAt']=m.now();q.save()
