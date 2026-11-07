"""Complete only missing anonymous401 assertion after retained exception-name typo.
Run while primary probe is waiting for UI; no fixture resources/processes acquired.
"""
import importlib.util,json,urllib.request,urllib.error
from pathlib import Path
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('m',P/'probe-f021-v174-base.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
e=P/'evidence';src=json.loads((e/'SRS_F021-V1.174-http-20261107.json').read_text(encoding='utf8'));old=next(x for x in src['cases'] if x['name']=='authorization-order-controls');tid=old['taskId'];op=m.l.API('运行操作员');before=op(f'/tasks/{tid}')
req=urllib.request.Request(m.l.BASE+f'/tasks/{tid}/terminate',data=b'{}',headers={'Content-Type':'application/json'},method='POST')
try:
 with urllib.request.urlopen(req,timeout=10) as res:ret={'http':res.status,'body':json.load(res)}
except urllib.error.HTTPError as err:ret={'http':err.code,'body':json.load(err)}
after=op(f'/tasks/{tid}')
x={'tag':'V1.174','productSha':m.SHA,'at':m.now(),'taskId':tid,'name':'authorization-order-controls-completed','source':'SRS_F021-V1.174-http-20261107.json','retainedDiagnostic':'urllib.erroHTTPError typo in initial probe, corrected to urllib.error.HTTPError; not product failure','priorConfigRequests':old['requests'],'before':before,'anonymousResponse':ret,'after':after,'checks':{'priorConfigBoth403':all(x['response']['http']==403 for x in old['requests']),'anonymous401':ret['http']==401,'noTaskMutation':before==after==old['before']['task']}}
(e/'SRS_F021-V1.174-auth-supplement-20261107.json').write_bytes(json.dumps(x,ensure_ascii=False,indent=2).encode('utf8'));assert all(x['checks'].values());print(x['checks'])
