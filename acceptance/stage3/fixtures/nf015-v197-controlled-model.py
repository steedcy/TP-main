"""Controlled NF015 V1.197 model fixture.

Synthetic only.  The handler accepts both Content-Length and chunked requests,
returns the exact goal/planning DTOs used by the external model adapter, and
supports deterministic fault modes selected by markers in taskGoal.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PORT = int(os.environ.get("NF015_MODEL_PORT", "18117"))
JOURNAL = Path(os.environ.get("NF015_MODEL_JOURNAL", str(ROOT / ".local-test/nf015-v197-model-requests.jsonl")))


def read_body(handler: BaseHTTPRequestHandler) -> bytes:
    transfer_encoding = handler.headers.get("Transfer-Encoding", "").lower()
    if "chunked" in transfer_encoding:
        chunks: list[bytes] = []
        while True:
            line = handler.rfile.readline()
            if not line:
                raise ConnectionError("request ended before terminating chunk")
            size = int(line.strip().split(b";", 1)[0], 16)
            if size == 0:
                while handler.rfile.readline().strip():
                    pass
                return b"".join(chunks)
            chunks.append(handler.rfile.read(size))
            if handler.rfile.read(2) != b"\r\n":
                raise ConnectionError("invalid chunk terminator")
    length = int(handler.headers.get("Content-Length", "0"))
    return handler.rfile.read(length)


def step(seq: int, capability: str, params: dict, condition: str, goal: str) -> dict:
    return {
        "stepSeq": seq,
        "stepGoal": goal,
        "capabilityType": capability,
        "inputParams": params,
        "precondition": "device online",
        "completionCondition": condition,
        "failureHandling": "manual handling",
        "stepTimeout": 60,
    }


def special_passenger_plan(req: dict) -> list[dict]:
    scene = req.get("sceneParams") or {}
    target = scene.get("targetLocation", "F2_TEST_GATE")
    assistance = scene.get("assistanceType", "synthetic assistance")
    notification = scene.get("notificationType", "BOTH")
    repeat = scene.get("repeatCount", 1)
    escort = scene.get("escortMode", "LEAD")
    duration = scene.get("maxDuration", 600)
    return [
        step(1, "CAP_INFO_DISPLAY", {
            "contentType": scene.get("contentType", "TEXT"),
            "contentData": assistance,
            "displayDuration": scene.get("displayDuration", 60),
        }, "displayStatus=SUCCESS", "publish synthetic assistance information"),
        step(2, "CAP_NOTIFICATION", {
            "notificationType": notification,
            "notificationContent": assistance,
            "repeatCount": repeat,
        }, "notificationStatus=SUCCESS", "notify synthetic assistance"),
        step(3, "CAP_ESCORT", {
            "targetLocation": target,
            "escortMode": escort,
            "maxDuration": duration,
        }, "arrivalStatus=ARRIVED", "escort synthetic passenger"),
    ]


def navigation_plan(req: dict) -> list[dict]:
    scene = req.get("sceneParams") or {}
    return [step(1, "CAP_NAVIGATION", {
        "targetLocation": scene.get("targetLocation", "F2_TEST_GATE"),
        "routePreference": scene.get("routePreference", "BARRIER_FREE"),
    }, "routeGenerated=true", "navigate synthetic route")]


def response_for(path: str, req: dict) -> tuple[int, dict | str]:
    marker = str(req.get("taskGoal", ""))
    if "NF015_MODEL_HTTP_503" in marker:
        return 503, {"error": "synthetic model unavailable"}
    if "NF015_MODEL_MALFORMED" in marker and path.endswith("/v1/planning/generate"):
        return 200, "{\"planSteps\":["
    if "NF015_MODEL_TIMEOUT" in marker:
        # Delay is controlled by the caller's timeout and is only used for the
        # explicit timeout scenario; the normal fixture never takes this path.
        import time
        time.sleep(90)

    if path.endswith("/v1/goal/understand"):
        return 200, {
            "resultCode": "0",
            "origin": "F2_TEST_SERVICE",
            "destination": (req.get("sceneParams") or {}).get("targetLocation", "F2_TEST_GATE"),
            "constraints": ["synthetic NF015 fixture", "steps <= 5"],
            "completionCondition": "routeGenerated=true",
            "infoComplete": True,
            "missingInfoQuestions": [],
            "unrelatedToAnyFamily": False,
            "inferredTaskFamily": req.get("taskFamily") or "SPECIAL_PASSENGER_SERVICE",
        }

    family = req.get("taskFamily") or "SPECIAL_PASSENGER_SERVICE"
    plan = special_passenger_plan(req) if family == "SPECIAL_PASSENGER_SERVICE" else navigation_plan(req)
    return 200, {
        "resultCode": "0",
        "planSteps": plan,
        "planRationale": "Controlled NF015 V1.197 synthetic model",
        "confidence": 0.99,
        "candidateDiverse": True,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "NF015ControlledModel/1.0"

    def log_message(self, *_args):
        return

    def do_POST(self):  # noqa: N802
        try:
            raw = read_body(self)
            req = json.loads(raw.decode("utf-8"))
            status, payload = response_for(self.path, req)
            record = {
                "at": datetime.now(timezone.utc).isoformat(),
                "phase": "goal" if self.path.endswith("/v1/goal/understand") else "planning",
                "path": self.path,
                "requestId": req.get("requestId"),
                "taskGoal": req.get("taskGoal"),
                "taskFamily": req.get("taskFamily"),
                "httpStatus": status,
            }
            JOURNAL.parent.mkdir(parents=True, exist_ok=True)
            with JOURNAL.open("a", encoding="utf-8", newline="\n") as journal:
                journal.write(json.dumps(record, ensure_ascii=False) + "\n")
            body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except Exception as exc:  # keep the fixture alive for the next case
            self.send_error(400, explain=str(exc))


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
