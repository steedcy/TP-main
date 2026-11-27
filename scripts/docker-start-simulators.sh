#!/usr/bin/env bash
# 通过后端 HTTP 接口批量拉起 Docker 容器内的所有活跃仿真体并等待上线
# 用法示例：
#   sudo bash /opt/airport-ai/repo/scripts/docker-start-simulators.sh
#   sudo bash /opt/airport-ai/repo/scripts/docker-start-simulators.sh --password <admin密码>

set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/airport-ai/repo}"
BASE_URL=""
ADMIN_USER=""
ADMIN_PASS=""
WAIT_ONLINE=true
TIMEOUT_SEC=90

log()  { printf '[INFO] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
die()  { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)   BASE_URL="${2:?缺少 --base-url 参数}"; shift 2 ;;
    --username)   ADMIN_USER="${2:?缺少 --username 参数}"; shift 2 ;;
    --password)   ADMIN_PASS="${2:?缺少 --password 参数}"; shift 2 ;;
    --no-wait)    WAIT_ONLINE=false; shift ;;
    --timeout)    TIMEOUT_SEC="${2:?缺少 --timeout 参数}"; shift 2 ;;
    -h|--help)
      cat <<EOF
用法: bash scripts/docker-start-simulators.sh [选项]
  --base-url <URL>     后端地址（默认读取 .env BACKEND_PORT，即 http://127.0.0.1:8080）
  --username <USER>    管理员用户名（默认读取 .env SIM_ADMIN_USERNAME 或 admin）
  --password <PASS>    管理员密码（默认读取 .env SIM_ADMIN_PASSWORD / ADMIN_PASSWORD）
  --no-wait            仅触发启动，不等待设备上线
  --timeout <SEC>      等待上线超时秒数（默认 90）
EOF
      exit 0 ;;
    *) die "未知参数: $1" ;;
  esac
done

if [[ -f "${REPO_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${REPO_DIR}/.env"
  set +a
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:${BACKEND_PORT:-8080}}"
ADMIN_USER="${ADMIN_USER:-${SIM_ADMIN_USERNAME:-admin}}"
ADMIN_PASS="${ADMIN_PASS:-${SIM_ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}}"

if [[ -z "${ADMIN_PASS}" && -f "${REPO_DIR}/user.md" ]]; then
  ADMIN_PASS="$(grep -E "admin|系统管理员" "${REPO_DIR}/user.md" | head -n1 | sed -E 's/.*[:：][[:space:]]*([^[:space:]]+).*/\1/' || true)"
fi

if [[ -z "${ADMIN_PASS}" ]]; then
  die "未提供管理员密码。请在 ${REPO_DIR}/.env 中配置 SIM_ADMIN_PASSWORD=<密码>，或传入 --password <密码>。"
fi

PYTHON_BIN=""
for cand in "$(command -v python3 2>/dev/null || true)" /usr/bin/python3 /usr/local/bin/python3; do
  if [[ -n "${cand}" && -x "${cand}" ]]; then
    PYTHON_BIN="${cand}"
    break
  fi
done
[[ -n "${PYTHON_BIN}" ]] || die "未找到 python3，请先安装：yum install -y python3"

export BASE_URL ADMIN_USER ADMIN_PASS WAIT_ONLINE TIMEOUT_SEC

"${PYTHON_BIN}" - <<'PYEOF'
import json
import os
import sys
import time
import urllib.error
import urllib.request

base = os.environ["BASE_URL"].rstrip("/") + "/api/v1"
user = os.environ["ADMIN_USER"]
password = os.environ["ADMIN_PASS"]
wait_online = os.environ.get("WAIT_ONLINE", "true").lower() == "true"
timeout_sec = int(os.environ.get("TIMEOUT_SEC", "90"))

def req(path, payload=None, token=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    m = method or ("POST" if payload is not None else "GET")
    r = urllib.request.Request(base + path, data=data, headers=headers, method=m)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e

login_res = req("/auth/login", {"username": user, "password": password})
token = login_res.get("data", {}).get("accessToken")
if not token:
    raise SystemExit(f"登录失败: {login_res}")

devices = req("/devices?page=1&size=200", token=token).get("data", {}).get("content", [])
simulators = [d for d in devices if d.get("isSimulator") and d.get("deviceStatus") == "ACTIVE"]
if not simulators:
    print("[INFO] 未发现需要启动的活跃仿真体设备。")
    sys.exit(0)

agents_res = req("/device-agents?page=1&size=200", token=token).get("data", {}).get("content", [])
online_codes = {a.get("deviceCode") for a in agents_res if a.get("onlineStatus") == "ONLINE"}

triggered = []
for d in simulators:
    code = d["deviceCode"]
    if code in online_codes:
        print(f"[INFO] {code}: 已在线，跳过")
        continue
    try:
        req(f"/devices/{code}/onboarding/retry", payload={}, token=token)
        print(f"[INFO] {code}: 已触发自动接入启动")
        triggered.append(code)
    except Exception as ex:
        if "409" in str(ex):
            print(f"[INFO] {code}: 正在启动中")
            triggered.append(code)
        else:
            print(f"[WARN] {code}: 启动失败 ({ex})", file=sys.stderr)

if wait_online and triggered:
    deadline = time.monotonic() + timeout_sec
    pending = set(triggered)
    while pending and time.monotonic() < deadline:
        agents_res = req("/device-agents?page=1&size=200", token=token).get("data", {}).get("content", [])
        now_online = {a.get("deviceCode") for a in agents_res if a.get("onlineStatus") == "ONLINE"}
        newly_up = pending & now_online
        for code in sorted(newly_up):
            print(f"[INFO] {code}: 已上线 (ONLINE)")
        pending -= newly_up
        if pending:
            time.sleep(2)
    if pending:
        print(f"[WARN] 以下仿真体在 {timeout_sec}s 内尚未完成心跳上线，请稍后在页面核查: {sorted(pending)}", file=sys.stderr)
    else:
        print(f"[INFO] 全部 {len(simulators)} 台仿真体已在线就绪。")
PYEOF
