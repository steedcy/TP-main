"""Controlled external model for SRS_F025 V1.186 verification.
Listens on 18117.
"""
import json, importlib.util, time
from pathlib import Path
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / '.local-test/f025-v186-cases.json'
JOURNAL = ROOT / '.local-test/f025-v186-model-requests.jsonl'

DEFAULT_F025_STEPS = [
    {
        "stepSeq": 1,
        "stepGoal": "在智慧航显发布特殊旅客会合信息与指引",
        "capabilityType": "CAP_INFO_DISPLAY",
        "inputParams": {
            "contentType": "TEXT",
            "contentData": "特殊旅客请在F2_GATE_A会合，工作人员即将到达协助",
            "displayDuration": 60
        },
        "precondition": "智慧航显正常在线",
        "completionCondition": "displayStatus=SUCCESS",
        "failureHandling": "失败重试一次后候选切换，仍失败转人工处理",
        "stepTimeout": 120
    },
    {
        "stepSeq": 2,
        "stepGoal": "移动机器人语音播报并提醒现场人员协助",
        "capabilityType": "CAP_NOTIFICATION",
        "inputParams": {
            "notificationType": "BOTH",
            "notificationContent": "轮椅协助服务已到达，请旅客准备出发",
            "repeatCount": 1
        },
        "precondition": "移动服务设备就绪",
        "completionCondition": "reportStatus=SUCCESS",
        "failureHandling": "失败重试一次后候选切换，仍失败转人工处理",
        "stepTimeout": 120
    },
    {
        "stepSeq": 3,
        "stepGoal": "移动机器人引导旅客由起点到达目的地",
        "capabilityType": "CAP_ESCORT",
        "inputParams": {
            "targetLocation": "F2_SERVICE_POINT",
            "escortMode": "LEAD",
            "maxDuration": 600
        },
        "precondition": "现场会合完成",
        "completionCondition": "escortCompleted=true",
        "failureHandling": "失败重试一次后候选切换，仍失败局部重规划",
        "stepTimeout": 300
    }
]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.headers.get('Transfer-Encoding', '').lower() == 'chunked':
            chunks = []
            while True:
                n = int(self.rfile.readline().strip().split(b';')[0], 16)
                if not n:
                    while self.rfile.readline().strip():
                        pass
                    break
                chunks.append(self.rfile.read(n))
                self.rfile.read(2)
            raw = b''.join(chunks)
        else:
            raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        
        req = json.loads(raw.decode('utf-8'))
        goal = req.get('taskGoal', '')
        case = {}
        if 'F186_UI_SPECIAL_PASSENGER' in goal:
            case = {
                'infoComplete': False,
                'origin': None,
                'destination': 'F2_SERVICE_POINT',
                'missingInfoQuestions': ['请补充服务起点']
            }
        elif CONFIG.exists():
            cases_dict = json.loads(CONFIG.read_text(encoding='utf-8'))
            for marker, value in cases_dict.items():
                if marker in goal:
                    case = value
                    break

        phase = 'goal' if self.path.endswith('/v1/goal/understand') else 'planning'
        status = case.get('goalHttpStatus' if phase == 'goal' else 'planHttpStatus', 200)

        if status != 200:
            data = b'{"error":"synthetic model error"}'
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if phase == 'goal':
            is_complete = case.get('infoComplete', True)
            missing = case.get('missingInfoQuestions', [])
            origin_val = case.get('origin', 'F2_GATE_A')
            clarify_rounds = req.get('clarificationAnswers') or []
            if clarify_rounds:
                has_origin = any('F2_' in str(ans) for r in clarify_rounds for ans in (r.get('answers', {}).values() if isinstance(r, dict) else []))
                if has_origin:
                    is_complete = True
                    missing = []
                    origin_val = 'F2_GATE_A'
                else:
                    is_complete = False
                    missing = ['请补充服务起点']
                    origin_val = ''
            response = {
                'resultCode': '0',
                'origin': origin_val,
                'destination': case.get('destination', 'F2_SERVICE_POINT'),
                'constraints': ['synthetic test'],
                'completionCondition': case.get('goalCompletion', 'escortCompleted=true'),
                'infoComplete': is_complete,
                'missingInfoQuestions': missing,
                'unrelatedToAnyFamily': False,
                'inferredTaskFamily': req.get('taskFamily') or 'SPECIAL_PASSENGER_SERVICE'
            }
            if 'goalOverride' in case:
                response.update(case['goalOverride'])
        else:
            replan = any('仅替换步骤' in str(c) for c in req.get('constraints', []))
            steps = case.get('replanSteps' if replan else 'steps')
            if steps is None:
                steps = DEFAULT_F025_STEPS
            response = {
                'resultCode': case.get('planResultCode', '0'),
                'planSteps': steps,
                'planRationale': 'Controlled F025 V186 model fixture',
                'confidence': 0.99,
                'candidateDiverse': False
            }

        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with JOURNAL.open('a', encoding='utf-8') as f:
            f.write(json.dumps({
                'at': datetime.now(timezone.utc).isoformat(),
                'phase': phase,
                'request': req,
                'response': response
            }, ensure_ascii=False) + '\n')

        data = json.dumps(response).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 18117), Handler)
    print("Controlled model listening on 18117...")
    server.serve_forever()
