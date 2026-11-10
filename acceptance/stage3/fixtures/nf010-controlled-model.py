"""Controlled external planning model mock for SRS_NF010 V1.192 verification.
Listens on port 18117.
Captures all LLM requests into .local-test/model-requests-nf010.jsonl.
"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[3]
JOURNAL = ROOT / '.local-test/model-requests-nf010.jsonl'

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
            scene_params = req.get('sceneParams') or {}
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
                'planRationale': 'SRS_NF010 controlled fixture baseline plan',
                'confidence': 0.99,
                'candidateDiverse': False,
                'planSteps': [
                    {
                        'stepSeq': 1,
                        'stepGoal': '广播现场通知',
                        'deviceType': 'SMART_DISPLAY',
                        'candidateCapabilities': ['CAP_INFO_DISPLAY'],
                        'preconditions': [],
                        'completionCondition': 'display=true',
                        'failureHandling': 'RETRY'
                    }
                ]
            }

        body = json.dumps(response, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    server = ThreadingHTTPServer(('127.0.0.1', 18117), Handler)
    print("Controlled model listening on 127.0.0.1:18117...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
