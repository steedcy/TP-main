"""After all live probes cleaned, run following owned JAR restart. Capture exact
first create response and count-derived code before request; preserve failed rows.
"""
import os,importlib.util,json
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='restart'
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('probe-f019-v168-round.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m
try:
 q.setup();q.ev['preRequestCount']=int(m.sql(f'select count(*) from {m.SC}.context_snapshots'));code=f"CTX-20261106-{q.ev['preRequestCount']+1:04d}";q.ev['predictedNextCode']=code;q.ev['existingCodeRows']=m.rows(f"select snapshot_code,task_id,generated_at from {m.SC}.context_snapshots where snapshot_code={m.lit(code)}");marker='F168_RESTART_EXACT_RESPONSE';q.cases[marker]={'steps':[h.st()],'goalCompletion':'routeGenerated=true','confidence':.99};(r.R/'.local-test/f019-v168-cases.json').write_text(json.dumps(q.cases),encoding='utf8');body={'taskGoal':marker+' synthetic navigation to F2_TEST_GATE','taskFamily':q.family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}};res=m.p.raw(q.op,'/tasks',body);row={'name':'jar-restart-snapshot-create','request':body,'response':res};q.ev['cases'].append(row);q.save();tid=m.sql(f'select id from {m.SC}.tasks where task_goal={m.lit(body["taskGoal"])} order by id desc limit 1');row['taskId']=int(tid) if tid else None
 if row['taskId']:q.tasks.append(row['taskId']);h.finish(row);r.capture(row)
 q.record(row,{'createHttp200':res['http'] in [200,201],'taskPersisted':bool(row['taskId']),'nextSnapshotCodeNotColliding':not bool(q.ev['existingCodeRows'])})
finally:q.cleanup();q.ev['endedAt']=m.now();q.save()
