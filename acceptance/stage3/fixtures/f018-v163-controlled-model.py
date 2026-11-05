import json,importlib.util
from pathlib import Path
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('base',Path(__file__).with_name('f013-v142-controlled-model.py'));base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
CONFIG=ROOT/'.local-test/f018-v163-cases.json';JOURNAL=ROOT/'.local-test/f018-v163-model-requests.jsonl'
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
  req=json.loads(raw);goal=req.get('taskGoal','');case={}
  if CONFIG.exists():
   for marker,value in json.loads(CONFIG.read_text(encoding='utf-8')).items():
    if marker in goal:case=value;break
  import time
  phase='goal' if self.path.endswith('/v1/goal/understand') else 'planning'
  time.sleep(case.get('goalDelay' if phase=='goal' else 'planDelay',0))
  replan=phase=='planning' and any('仅替换步骤' in str(c) for c in req.get('constraints',[]))
  status=case.get('replanHttpStatus' if replan else ('goalHttpStatus' if phase=='goal' else 'planHttpStatus'),200)
  if status != 200 or (phase=='planning' and case.get('planMode')=='MALFORMED'):
   data=b'{"planSteps":' if status==200 else b'{"error":"synthetic isolated model unavailable"}'
   with JOURNAL.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'phase':phase,'request':req,'httpStatus':status,'rawResponse':data.decode()},ensure_ascii=False)+'\n')
   self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  if phase=='goal':
   response={'resultCode':'0','origin':'F2_SERVICE_POINT','destination':'F2_TEST_GATE','constraints':['synthetic test'],'completionCondition':case.get('goalCompletion','routeGenerated=true'),'infoComplete':True,'missingInfoQuestions':[],'unrelatedToAnyFamily':False,'inferredTaskFamily':req.get('taskFamily') or 'EXT_2AD8B934'}
  else:
   replan=any('仅替换步骤' in str(c) for c in req.get('constraints',[]))
   steps=case.get('replanSteps') if replan else case.get('steps')
   if steps is None:steps=base.plan(goal)
   response={'resultCode':'0','planSteps':steps,'planRationale':'Controlled F018 V163 fixture','confidence':case.get('confidence',0.99),'candidateDiverse':case.get('diverse',False)}
  with JOURNAL.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'phase':phase,'request':req,'response':response},ensure_ascii=False)+'\n')
  data=json.dumps(response).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
if __name__=='__main__':
 JOURNAL.parent.mkdir(exist_ok=True);ThreadingHTTPServer(('127.0.0.1',18117),Handler).serve_forever()
