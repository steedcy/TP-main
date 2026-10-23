"""Local deterministic planning fixture. Never substitutes for real Kimi quality tests.
127.0.0.1:8099; .local-test/planning-fault.json selects goal/planning/replanning modes:
success, unavailable, failure, timeout, malformed, too_many_steps, safety, low_confidence.
The request journal excludes HTTP headers and credentials.
"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import datetime,json,time
ROOT=Path(__file__).resolve().parents[1];LOCAL=ROOT/'.local-test';LOCAL.mkdir(exist_ok=True)
MODE=LOCAL/'planning-fault.json'
if not MODE.exists(): MODE.write_text(json.dumps({'goal':'success','planning':'success','replanning':'success','delaySeconds':65}),encoding='utf-8')

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        if self.path not in ['/v1/goal/understand','/v1/planning/generate']: self.send_error(404);return
        if self.headers.get('Transfer-Encoding','').lower()=='chunked':
            chunks=[]
            while True:
                size=int(self.rfile.readline().strip().split(b';')[0],16)
                if not size:
                    while self.rfile.readline().strip(): pass
                    break
                chunks.append(self.rfile.read(size));self.rfile.read(2)
            raw=b''.join(chunks)
        else: raw=self.rfile.read(int(self.headers.get('Content-Length',0)))
        try: body=json.loads(raw)
        except Exception: self.send_error(400,'Invalid JSON body');return
        is_replan=bool(body.get('completedSteps')) or any('保留已完成' in str(c) for c in body.get('constraints',[]))
        phase='goal' if self.path.endswith('/understand') else 'replanning' if is_replan else 'planning'
        mode=json.loads(MODE.read_text(encoding='utf-8'))
        selected=mode.get(phase,'success')
        with (LOCAL/'planning-requests.jsonl').open('a',encoding='utf-8') as out:
            out.write(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'phase':phase,'mode':selected,'request':body},ensure_ascii=False)+'\n')
        if selected=='timeout': time.sleep(max(61,float(mode.get('delaySeconds',65))))
        if selected=='unavailable': self.send_error(503,'Controlled service unavailable');return
        if selected=='malformed':
            self.send_response(200);self.end_headers();self.wfile.write(b'{not-json');return
        if selected=='failure': result={'resultCode':'1003','errorMessage':'Controlled model failure'}
        elif phase=='goal':
            result={'resultCode':'0','origin':'F2_SERVICE_POINT','destination':body.get('sceneParams',{}).get('targetLocation','F2_TEST_GATE'),
                    'constraints':['不得下发运动安全控制指令'],'completionCondition':'既定业务完成条件满足','infoComplete':True,
                    'missingInfoQuestions':[],'unrelatedToAnyFamily':False,'inferredTaskFamily':body.get('taskFamily','FLIGHT_CHANGE_RESPONSE')}
        else:
            fixture=next(f for f in json.loads((ROOT/'scripts/test-fixtures/baselines.json').read_text(encoding='utf-8')) if f['taskFamily']==body['taskFamily'])
            inputs={p['name']:p.get('defaultValue') for p in fixture['inputParams']};inputs.update(body.get('sceneParams') or {})
            steps=[]
            for i,step in enumerate(fixture['steps'],1):
                values={p['target']:inputs[p['source'].removeprefix('TEMPLATE_INPUT.')] for p in step['paramMapping'] if p['source'].startswith('TEMPLATE_INPUT.')}
                if step['capabilityType']=='CAP_OVERSIZE_ALERT': values['baggageInfo']=json.dumps({'length':80,'width':55,'height':35,'weight':35})
                steps.append({'stepSeq':i,'stepGoal':'执行既定'+step['capabilityType'],'capabilityType':step['capabilityType'],
                    'inputParams':values,'precondition':'设备在线空闲且前序步骤完成','completionCondition':step['completionCondition'],
                    'failureHandling':'一次重试、候选切换，失败转局部重新规划或人工','stepTimeout':step['stepTimeout']})
            if phase=='replanning': steps=steps[len(body.get('completedSteps') or []):]
            override=mode.get('replanPlanSteps' if phase=='replanning' else 'initialPlanSteps')
            if isinstance(override,list): steps=override
            if selected=='too_many_steps': steps=[dict(steps[0],stepSeq=i) for i in range(1,7)]
            if selected=='safety': steps[0]['inputParams']['speedLimit']=2
            result={'resultCode':'0','planSteps':steps,'planRationale':'本机可重复故障条件','confidence':0.2 if selected=='low_confidence' else 0.99,'candidateDiverse':False}
        try:
            raw=json.dumps(result,ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError): pass

if __name__=='__main__':
    print('Local planning fault fixture listening on 127.0.0.1:8099',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8099),Handler).serve_forever()
