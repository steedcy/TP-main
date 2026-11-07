"""Final read-only cross-layer audit consistency; no business actions repeated."""
import importlib.util,json,hashlib,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=R/'acceptance/stage3/evidence'
s=importlib.util.spec_from_file_location('m',R/'acceptance/stage3/probe-f021-v174-base.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
source=json.loads((E/'SRS_F021-V1.174-http-20261107.json').read_text(encoding='utf8'));op=m.l.API('运行操作员');out={'at':m.now(),'productSha':m.SHA,'tag':'V1.174','taskIds':source['taskIds'],'observations':[],'businessExecutionsAdded':0}
for tid in source['taskIds']:
 events=op(f'/tasks/{tid}/events');sqlrows=m.rows(f'select row_to_json(x)::text from {m.SC}.task_events x where task_id={tid} order by id');byid={r['id']:r for r in sqlrows};structured=[]
 for ev in events:
  if ev['eventType'] not in ['TASK_TERMINATED','MANUAL_TERMINATED']:continue
  parsed=json.loads(ev['detail']);structured.append({'eventId':ev['id'],'type':ev['eventType'],'parsed':parsed,'checks':{'requiredFields':all(k in parsed for k in ['reason','previousStatus','operator','deviceCancelResults','summary']),'summaryMatches':ev['detailSummary']==parsed['summary'],'sqlRawEqualsDetail':byid[ev['id']]['detail_summary']==ev['detail'],'allDeviceFields':all(all(d.get(k) for k in ['deviceCode','agentId','cancelCommandId','cancelStatus']) for d in parsed['deviceCancelResults'])}})
 out['observations'].append({'taskId':tid,'httpEvents':events,'sqlRows':sqlrows,'structured':structured,'checks':{'sameEventIds':{e['id'] for e in events}==set(byid),'allRawDetailMatches':all(e['detail']==byid[e['id']]['detail_summary'] for e in events),'allStructuredAssertions':all(all(x['checks'].values()) for x in structured)}})
ui=json.loads((E/'SRS_F021-V1.174-ui-20261107.json').read_text(encoding='utf8'));actual=next(x for x in ui['cases'] if x['name']=='actual-browser-termination');ev=next(x for x in out['observations'] if x['taskId']==actual['taskId'])
out['browserTimelineMatchesStructuredSummary']=all(any(e['eventType'] in t and json.loads(e['detail'])['summary'] in t for t in actual['timeline']) for e in ev['httpEvents'] if e['eventType'] in ['TASK_TERMINATED','MANUAL_TERMINATED'])
out['structuredEventCount']=sum(len(x['structured']) for x in out['observations']);out['allPass']=all(all(x['checks'].values()) for x in out['observations']) and out['browserTimelineMatchesStructuredSummary']
out['jarSha256']=hashlib.sha256((R/'backend/target/airport-ai-app-1.0.0.jar').read_bytes()).hexdigest();out['productDiff']=subprocess.check_output(['git','diff','V1.174','--','backend','frontend'],cwd=R,encoding='utf8')
(E/'SRS_F021-V1.174-final-consistency-20261107.json').write_bytes(json.dumps(out,ensure_ascii=False,indent=2).encode('utf8'))
assert out['allPass'] and not out['productDiff'];print('All final SQL/HTTP/summary consistency checks passed; structured events',out['structuredEventCount'],'tasks',len(out['taskIds']))
