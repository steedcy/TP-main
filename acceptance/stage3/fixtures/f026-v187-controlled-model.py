"""Controlled external model for SRS_F026 V1.187 verification.
Listens on 18117.
"""
import json, importlib.util, time
from pathlib import Path
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / '.local-test/f026-v187-cases.json'
JOURNAL = ROOT / '.local-test/f026-v187-model-requests.jsonl'

DEFAULT_F026_STEPS = [
    {
        "stepSeq": 1,
        "stepGoal": "在航延屏发布航班变更信息",
        "capabilityType": "CAP_FLIGHT_UPDATE",
        "inputParams": {
            "flightNumber": "CA1234",
            "updateType": "GATE_CHANGE",
            "updateContent": "虚构航班CA1234登机口变更至F2_TEST_GATE",
            "displayDuration": 60
        },
        "precondition": "航延屏在线可用",
        "completionCondition": "publishStatus=SUCCESS",
        "failureHandling": "失败重试一次后候选切换，仍失败转人工处理",
        "stepTimeout": 120
    },
    {
        "stepSeq": 2,
        "stepGoal": "在智慧航显发布航班登机口变更与路径指引",
        "capabilityType": "CAP_INFO_DISPLAY",
        "inputParams": {
            "contentType": "TEXT",
            "contentData": "虚构航班CA1234旅客请前往F2_TEST_GATE登机",
            "displayDuration": 60
        },
        "precondition": "智慧航显正常在线",
        "completionCondition": "displayStatus=SUCCESS",
        "failureHandling": "失败重试一次后候选切换，仍失败转人工处理",
        "stepTimeout": 120
    },
    {
        "stepSeq": 3,
        "stepGoal": "移动机器人进行现场广播通知与提醒",
        "capabilityType": "CAP_NOTIFICATION",
        "inputParams": {
            "notificationType": "BOTH",
            "notificationContent": "虚构航班CA1234登机口已变更至F2_TEST_GATE，请留意改道",
            "repeatCount": 1
        },
        "precondition": "移动服务设备就绪",
        "completionCondition": "notificationStatus=SUCCESS",
        "failureHandling": "失败重试一次后候选切换，仍失败转人工处理",
        "stepTimeout": 120
    },
    {
        "stepSeq": 4,
        "stepGoal": "移动机器人改道空间意图引导",
        "capabilityType": "CAP_NAVIGATION",
        "inputParams": {
            "targetLocation": "F2_TEST_GATE",
            "routePreference": "BARRIER_FREE"
        },
        "precondition": "移动服务设备就绪",
        "completionCondition": "routeGenerated=true",
        "failureHandling": "失败重试一次后候选切换，仍失败局部重规划",
        "stepTimeout": 120
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
        if CONFIG.exists():
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
            resp = {
                'resultCode': '0',
                'taskGoal': goal,
                'inferredTaskFamily': req.get('taskFamily') or 'FLIGHT_CHANGE_RESPONSE',
                'origin': case.get('origin', None),
                'destination': case.get('destination', 'F2_TEST_GATE'),
                'constraints': case.get('constraints', []),
                'completionCondition': '航班变更通知与引导完成',
                'infoComplete': case.get('infoComplete', True),
                'missingInfoQuestions': case.get('missingInfoQuestions', []),
                'unrelatedToAnyFamily': case.get('unrelatedToAnyFamily', False)
            }
        else:
            steps = case.get('steps', DEFAULT_F026_STEPS)
            resp = {
                'resultCode': '0',
                'planSteps': steps,
                'planRationale': '航班变动三渠道应急协同响应计划',
                'confidence': case.get('confidence', 0.95),
                'candidateDiverse': False
            }

        journal_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'path': self.path,
            'request': req,
            'response': resp
        }
        with JOURNAL.open('a', encoding='utf-8') as f:
            f.write(json.dumps(journal_entry, ensure_ascii=False) + '\n')

        data = json.dumps(resp, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

def run():
    server = ThreadingHTTPServer(('127.0.0.1', 18117), Handler)
    print("Controlled model server listening on 18117...")
    server.serve_forever()

if __name__ == '__main__':
    run()
