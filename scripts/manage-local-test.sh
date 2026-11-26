#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOL="$SCRIPT_DIR/local-test-environment.py"

PYTHON_BIN=""
for candidate in \
  "$(command -v python3 2>/dev/null || true)" \
  "/usr/bin/python3" \
  "/usr/local/bin/python3" \
  "/opt/rh/rh-python38/root/usr/bin/python3" \
  "/opt/rh/rh-python36/root/usr/bin/python3" \
  "$(command -v python 2>/dev/null || true)"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "Error: Python 3 is required (CentOS 7 default 'python' is Python 2.7)." >&2
  echo "Install Python 3 first: yum install -y python3" >&2
  exit 1
fi

export PYTHONIOENCODING=utf-8

ACTION="${1:-status}"
ARG2="${2:-}"
ARG3="${3:-}"

cd "$TIP_ROOT"

case "$ACTION" in
  start-all)
    "$PYTHON_BIN" "$TOOL" start-all
    ;;
  start)
    "$PYTHON_BIN" "$TOOL" backend
    "$PYTHON_BIN" "$TOOL" start
    ;;
  frontend)
    "$PYTHON_BIN" "$TOOL" frontend
    ;;
  stop)
    "$PYTHON_BIN" "$TOOL" stop "${ARG2:-*}"
    ;;
  status)
    "$PYTHON_BIN" "$TOOL" status
    ;;
  configure)
    "$PYTHON_BIN" "$TOOL" configure
    ;;
  model-fixture)
    "$PYTHON_BIN" "$TOOL" model-fixture
    ;;
  device-fault)
    "$PYTHON_BIN" "$TOOL" fault "$ARG2" "$ARG3"
    ;;
  use-kimi)
    "$PYTHON_BIN" "$TOOL" stop backend
    "$PYTHON_BIN" "$TOOL" backend --provider moonshot
    ;;
  use-fault-model)
    "$PYTHON_BIN" "$TOOL" stop backend
    "$PYTHON_BIN" "$TOOL" backend --provider fault
    ;;
  *)
    echo "Usage: $0 {start-all|start|frontend|stop|status|configure|model-fixture|device-fault <device> <mode>|use-kimi|use-fault-model}" >&2
    exit 2
    ;;
esac
