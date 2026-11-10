"""Controlled external planning model mock for SRS_NF003 V1.191 verification.
Listens on port 18117.
Captures all LLM requests into .local-test/model-requests-nf003.jsonl for zero-leakage auditing.
"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[3]
JOURNAL = ROOT / '.local-test/model-requests-nf003.jsonl'

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.headers.get('Transfer-Encoding', '').lower() == 'chunked':
            chunks = []
            while True:
                line = self.rfile.readline().strip().split(b';')[0]
                if not line:
                    continue
                n = int(line, 16)
                if not n:
                    while self.rfile.readline().strip():
                        pass
                    break
                chunks.append(self.rfile.read(n))
                self.rfile.read(2) # CRLF
            raw = b''.join(chunks)
        else:
            content_len = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(content_len) if content_len > 0 else b'{}'

        try:
            req = json.loads(raw.decode('utf-8'))
        except Exception:
            req = {'raw': raw.decode('utf-8', errors='replace')}

        phase = 'goal' if self.path.endswith('/v1/goal/understand') else 'planning'
        
        # 记录模型请求日志供审查
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with JOURNAL.open('a', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps({
                'at': datetime.now(timezone.utc).isoformat(),
                'path': self.path,
                'phase': phase,
                'request': req
            }, ensure_ascii=False) + '\n')

        if phase == 'goal':
            task_family = req.get('taskFamily') or 'SPECIAL_PASSENGER_SERVICE'
            goal = req.get('taskGoal', '')
            scene_params = req.get('sceneParams') or {}
            
            # 如果是特殊旅客且缺少起点，则要求补充起点
            if '协助' in goal and not scene_params.get('origin') and '缺少起点' in goal:
                response = {
                    'resultCode': '0',
                    'origin': None,
                    'destination': 'F2_TEST_GATE',
                    'constraints': [],
                    'completionCondition': 'arrived=true',
                    'infoComplete': False,
                    'missingInfoQuestions': ['请提供协助起点'],
                    'unrelatedToAnyFamily': False,
                    'inferredTaskFamily': task_family
                }
            else:
                response = {
                    'resultCode': '0',
                    'origin': scene_params.get('origin', 'F2_TEST_GATE'),
                    'destination': scene_params.get('destination', scene_params.get('targetLocation', 'F2_ZONE_A')),
                    'constraints': [],
                    'completionCondition': 'completed=true',
                    'infoComplete': True,
                    'missingInfoQuestions': [],
                    'unrelatedToAnyFamily': False,
                    'inferredTaskFamily': task_family
                }
        else:
            response = {
                'resultCode': '0',
                'planRationale': 'SRS_NF003 controlled fixture baseline plan',
                'confidence': 0.99,
                'candidateDiverse': False,
                'planSteps': [
                    {
                        'stepSeq': 1,
                        'stepGoal': '会合旅客',
                        'deviceType': 'MOBILE_ROBOT',
                        'candidateCapabilities': ['CAP_NOTIFICATION', 'CAP_NAVIGATION'],
                        'preconditions': [],
                        'completionCondition': 'rendezvous=true',
                        'failureHandling': 'RETRY'
                    },
                    {
                        'stepSeq': 2,
                        'stepGoal': '陪同引导前往目的地',
                        'deviceType': 'MOBILE_ROBOT',
                        'candidateCapabilities': ['CAP_NAVIGATION'],
                        'preconditions': ['rendezvous=true'],
                        'completionCondition': 'arrived=true',
                        'failureHandling': 'DOWNGRADE'
                    }
                ]
            }

        body = json.dumps(response).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    port = 18117
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'NF003 controlled model running on port {port}...')
    server.serve_forever()
