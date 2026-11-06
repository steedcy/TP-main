"""Filter-only synthetic catalog, nine states/two dates/literal SQL wildcards.
No natural lifecycle claim. SQL seeds own schema only; public API queries and
termination cleanup preserve all seeded rows for evidence.
"""
import importlib.util,json,time
from pathlib import Path
from urllib.parse import urlencode
P=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('m',P/'probe-f020-v171.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
out=P/'evidence/SRS_F020-V1.171-filter-catalog-stable2-20261106.json';assert not out.exists()
op=m.l.API('运行操作员');SC=m.SC;ev={'tag':'V1.171','productSha':m.SHA,'startedAt':m.now(),'fixtureLevel':'SQL synthetic catalog, only filter equivalence/boundaries, no lifecycle or planning P','rows':[],'queries':[],'checks':{},'cleanup':[]}
prior=json.loads((P/'evidence/SRS_F020-V1.171-http-20261106-final.json').read_text(encoding='utf8'));family=prior['cases'][0]['after']['task']['taskFamily']
sqlraw=m.sql
m.sql=lambda query:'\n'.join(x for x in sqlraw(query).splitlines() if not x.startswith('INSERT 0 '))
ev['priorProbeRows']=m.rows(f"select * from {SC}.tasks where task_code like 'G171C-%'")
for x in ev['priorProbeRows']:
 m.sql(f"update {SC}.tasks set task_goal='F171_PROBE_DIAGNOSTIC_753 preserved original goal in catalog evidence' where id={x['id']}")
 ev['cleanup'].append({'id':x['id'],'response':m.p.raw(op,f"/tasks/{x['id']}/terminate",{'reason':'Synthetic catalog probe repair, row preserved','confirmed':True})})
try:
 for i,status in enumerate(['PLANNING','SUPERVISING','PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING','COMPLETED','FAILED','PENDING_MANUAL','MANUAL_TERMINATED']):
  code='G171C-'+str(time.time_ns());goal=f"F171_CATALOG_{i} literal%_\\quote' boundary";q=f"insert into {SC}.tasks(task_code,task_goal,task_family,scene_params,status,replan_used,is_dry_run,created_at,updated_at,created_by) values({m.lit(code)},{m.lit(goal)},{m.lit(family)},'{{}}'::json,{m.lit(status)},false,false,date_trunc('day',now())+interval '{8+i} hour',now(),'GPT Synthetic Operator') returning id"
  tid=int(m.sql(q));ev['rows'].append({'id':tid,'status':status,'goal':goal,'code':code})
 old=int(m.sql(f"insert into {SC}.tasks(task_code,task_goal,task_family,status,replan_used,is_dry_run,created_at,updated_at,created_by) values('G171OLD-{time.time_ns()}','F171_CATALOG_OLD',{m.lit(family)},'COMPLETED',false,false,date_trunc('day',now())-interval '9 hour',now(),'GPT Synthetic Operator') returning id"));ev['oldId']=old
 for x in ev['rows']:
  params={'goalKeyword':'F171_CATALOG_','taskFamily':family,'status':x['status'],'size':100};ret=op('/tasks?'+urlencode(params));ev['queries'].append({'params':params,'response':ret});expected=[z['id'] for z in ev['rows'] if z['status']==x['status']]+([old] if x['status']=='COMPLETED' else []);ev['checks'][x['status']]=sorted(z['id'] for z in ret['content'])==sorted(expected)
 ids=[x['id'] for x in ev['rows']];ret=op('/tasks?'+urlencode({'goalKeyword':'F171_CATALOG_','createdFrom':'2026-11-06T00:00:00','createdTo':'2026-11-06T23:59:59','size':100}));ev['todayResponse']=ret;ev['checks']['todayExcludesYesterday']=sorted(z['id'] for z in ret['content'])==sorted(ids)
 ret=op('/tasks?'+urlencode({'goalKeyword':"literal%_\\quote'",'size':100}));ev['literalResponse']=ret;ev['checks']['sqlWildcardsLiteral']=sorted(z['id'] for z in ret['content'])==sorted(ids)
 # Read-only inclusive created_at bounds and cross-family empty conjunction.
 for params,expected in [({'goalKeyword':'F171_CATALOG_','taskFamily':'EXT_F020_NONEXISTENT','size':100},[]),({'goalKeyword':'F171_CATALOG_','createdFrom':'2026-11-06T08:00:00','createdTo':'2026-11-06T08:00:00'},[ids[0]])]:
  ret=op('/tasks?'+urlencode(params));ev['queries'].append({'params':params,'response':ret});ev['checks']['emptyFamily' if not expected else 'inclusiveExactTime']=[z['id'] for z in ret['content']]==expected
except Exception as e:
 ev['diagnostic']=str(e);ev['stderr']=getattr(e,'stderr',None)
finally:
 for x in ev['rows']:
  if x['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:
   ev['cleanup'].append({'id':x['id'],'response':m.p.raw(op,f"/tasks/{x['id']}/terminate",{'reason':'Synthetic F020 filter fixture cleanup','confirmed':True})})
 ev['endedAt']=m.now();out.write_text(json.dumps(ev,ensure_ascii=False,indent=2),encoding='utf8')
print(ev['checks'],ev.get('diagnostic'))
