"""Deterministic F013 model fixture; synthetic inputs only, listens on GPT port18117."""
import json
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];JOURNAL=ROOT/'.local-test/f013-v142-model-requests.jsonl'
def step(seq=1):
 return {'stepSeq':seq,'stepGoal':f'Synthetic navigation {seq}','capabilityType':'CAP_NAVIGATION','inputParams':{'targetLocation':'F2_TEST_GATE'},'precondition':'device online','completionCondition':'routeGenerated=true','failureHandling':'最多重试2次后转人工','stepTimeout':60}
def plan(goal):
 ss=[step()]
 if 'SIX' in goal:ss=[step(i) for i in range(1,7)]
 if 'FIVE' in goal:ss=[step(i) for i in range(1,6)]
 if 'FORWARD' in goal:ss=[step(1),step(2)];ss[0]['precondition']='after step 2'
 if 'SELF' in goal:ss[0]['precondition']='依赖步骤1完成'
 if 'DEPENDENCY_MISSING' in goal:ss[0]['precondition']='depends on step 99'
 if 'VALID_DEP' in goal:ss=[step(1),step(2)];ss[1]['precondition']='步骤1完成后执行'
 for f in ['stepGoal','capabilityType','inputParams','precondition','completionCondition','failureHandling']:
  if 'MISSING_'+f in goal:ss[0].pop(f)
 if 'LOOP' in goal:ss[0]['precondition']='while(true) { repeat forever; }'
 if 'DYNAMIC' in goal:ss[0]['inputParams']['nested']={'code':'eval(nextAction())'}
 if 'NEGOTIATION' in goal:ss[0]['failureHandling']='unlimited rounds of negotiation'
 if 'FAKE_CAP' in goal:ss[0]['capabilityType']='CAP_F013_FICTIONAL'
 if 'DISABLED_CAP' in goal:ss[0]['capabilityType']='CAP_BAGGAGE_MEASURE'
 if 'NO_CANDIDATE' in goal:ss[0]['capabilityType']='CAP_INFO_DISPLAY'
 if 'OUTSIDE_TASK' in goal:ss[0]['capabilityType']='CAP_ESCORT'
 if 'MOTION' in goal:ss[0]['inputParams']['speed']=2
 if 'BAD_PARAM' in goal:ss[0]['inputParams']['routePreference']='INVALID_ROUTE_F013'
 if 'MULTI' in goal:
  ss[0].pop('precondition');ss[0]['capabilityType']='CAP_F013_FICTIONAL';ss[0]['inputParams']['speed']=2
 return ss
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  if self.headers.get('Transfer-Encoding','').lower()=='chunked':
   chunks=[]
   while True:
    n=int(self.rfile.readline().strip().split(b';')[0],16)
    if not n:
     while self.rfile.readline().strip():pass
     break
    chunks.append(self.rfile.read(n));self.rfile.read(2)
   raw=b''.join(chunks)
  else:raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
  req=json.loads(raw);goal=req.get('taskGoal','');phase='goal' if self.path.endswith('/v1/goal/understand') else 'planning'
  with JOURNAL.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'phase':phase,'request':req},ensure_ascii=False)+'\n')
  if phase=='goal':
   response={'resultCode':'0','origin':'F2_SERVICE_POINT','destination':'F2_TEST_GATE','constraints':['synthetic test'],'completionCondition':'routeGenerated=true','infoComplete':True,'missingInfoQuestions':[],'unrelatedToAnyFamily':False,'inferredTaskFamily':req.get('taskFamily') or 'EXT_2AD8B934'}
  else:response={'resultCode':'0','planSteps':plan(goal),'planRationale':'Controlled F013 independent fixture','confidence':0.99,'candidateDiverse':False}
  data=json.dumps(response).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
if __name__=='__main__':
 JOURNAL.parent.mkdir(exist_ok=True);ThreadingHTTPServer(('127.0.0.1',18117),Handler).serve_forever()
