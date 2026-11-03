import json,time
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

root=Path(__file__).resolve().parents[3]
(root/'.local-test').mkdir(exist_ok=True)
journal=root/'.local-test/gpt-f012-v139-model-requests.jsonl'

def step(seq,**changes):
    value={'stepSeq':seq,'stepGoal':f'Synthetic navigation action {seq}',
           'capabilityType':'CAP_NAVIGATION','inputParams':{'targetLocation':'F2_TEST_GATE'},
           'precondition':'device online','completionCondition':'routeGenerated=true',
           'failureHandling':'manual','stepTimeout':60}
    value.update(changes)
    return value

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def do_POST(self):
        try:
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
            request=json.loads(raw);goal=request.get('taskGoal','')
            phase='goal' if self.path.endswith('/v1/goal/understand') else 'planning'
            with journal.open('a',encoding='utf-8') as f:
                f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'phase':phase,'request':request},ensure_ascii=False)+'\n')
            if phase=='goal':
                response={'resultCode':'0','origin':'F2_SERVICE_POINT','destination':'F2_TEST_GATE',
                          'constraints':['synthetic test only'],'completionCondition':'routeGenerated=true',
                          'infoComplete':True,'missingInfoQuestions':[],'unrelatedToAnyFamily':False,
                          'inferredTaskFamily':request.get('taskFamily') or 'SPECIAL_PASSENGER_SERVICE'}
            elif self.path.endswith('/v1/planning/generate'):
                if 'F012_TIMEOUT' in goal:time.sleep(65)
                if 'F012_BAD_JSON' in goal:
                    data=b'not-json';self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
                if 'F012_ERROR' in goal:response={'resultCode':'1003','errorMessage':'Controlled planning failure'}
                else:
                    if 'F012_COND5' in goal:
                        steps=[{'stepSeq':1,'nodeType':'CONDITION','condition':'assistanceType is wheelchair'}]
                        steps += [step(i,**({'branchOf':1} if i==2 else {})) for i in range(2,7)]
                    elif 'F012_SIX' in goal:steps=[step(i) for i in range(1,7)]
                    elif 'F012_REPLAN4' in goal and request.get('completedSteps'):
                        steps=[step(i) for i in range(1,5)]
                    elif 'F012_REPLAN3' in goal and request.get('completedSteps'):
                        steps=[step(i) for i in range(1,4)]
                    elif 'F012_REPLAN4' in goal or 'F012_REPLAN3' in goal:
                        steps=[step(i) for i in range(1,6)]
                    elif 'F012_REPLAN5' in goal:steps=[step(i) for i in range(1,6)]
                    else:steps=[step(1)]
                    target=steps[-1]
                    if 'F012_MISSING_PRE' in goal:target.pop('precondition')
                    if 'F012_MISSING_FAIL' in goal:target.pop('failureHandling')
                    if 'F012_LOOP_PRE' in goal:target['precondition']='while(true) { repeat this display step forever; }'
                    if 'F012_LOOP_PARAM' in goal:target['inputParams']['__loop__']='eval(nextAction())'
                    if 'F012_FAKE_CAP' in goal:target['capabilityType']='CAP_FICTIONAL_F012'
                    if 'F012_DISABLED_CAP' in goal:target['capabilityType']='CAP_BAGGAGE_MEASURE'
                    if 'F012_MOTION' in goal:target['inputParams']['waypointList']=['F2_TEST_GATE']
                    if 'F012_LEGAL_NAV' in goal:target['completionCondition']='routeGenerated=true and waypointCount>0'
                    if 'F012_LEGAL_RETRY' in goal:target['failureHandling']='最多重试2次后转人工'
                    response={'resultCode':'0','planSteps':steps,'planRationale':'Controlled F012 fixture',
                              'confidence':0.99,'candidateDiverse':False}
            else:self.send_error(404);return
            data=json.dumps(response).encode()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

ThreadingHTTPServer(('127.0.0.1',18117),Handler).serve_forever()
