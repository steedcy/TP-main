#!/usr/bin/env bash
# CentOS 7 测试服务器 Docker Compose 版本一键更新与回滚脚本
# 用法示例：
#   1. 使用源码包一键备份并更新：
#      sudo bash /opt/airport-ai/repo/scripts/docker-update.sh --src /tmp/airport-ai-src.tar.gz
#   2. 使用离线镜像包一键备份并更新（免源码编译）：
#      sudo bash /opt/airport-ai/repo/scripts/docker-update.sh --load-images /tmp/airport-ai-images.tar.gz
#   3. 查看历史备份列表：
#      sudo bash /opt/airport-ai/repo/scripts/docker-update.sh --list-backups
#   4. 一键回滚到指定时间戳版本（含代码与数据库）：
#      sudo bash /opt/airport-ai/repo/scripts/docker-update.sh --rollback 20261119_163000

set -euo pipefail

# 若当前脚本位于 /opt/airport-ai/repo/scripts 下，需要在清理 repo 目录前将自身复制到 /tmp 执行
if [[ "${AIRPORT_UPDATE_REEXEC:-0}" != "1" ]]; then
  TMP_RUNNER="/tmp/airport-ai-docker-update-$$.sh"
  cp -f "${BASH_SOURCE[0]}" "${TMP_RUNNER}"
  chmod +x "${TMP_RUNNER}"
  export AIRPORT_UPDATE_REEXEC=1
  exec bash "${TMP_RUNNER}" "$@"
fi
trap 'rm -f "/tmp/airport-ai-docker-update-$$.sh" 2>/dev/null || true' EXIT

REPO_DIR="${REPO_DIR:-/opt/airport-ai/repo}"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/airport-ai/backup}"
SRC_ARCHIVE=""
LOAD_IMAGES=""
SERVER_IP=""
ROLLBACK_TS=""
LIST_BACKUPS=false
SKIP_DB_RESTORE=false
SKIP_SIMULATORS=false
ADMIN_USER=""
ADMIN_PASS=""
KEEP_BACKUPS="${KEEP_BACKUPS:-10}"

log()  { printf '[INFO] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
die()  { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
用法: sudo bash scripts/docker-update.sh [选项]

更新选项:
  --src <TAR.GZ>              新版本源码压缩包路径（默认: /tmp/airport-ai-src.tar.gz）
  --load-images <TAR.GZ>      使用离线镜像包更新（跳过 Maven/npm 源码编译）
  --server-ip <IP/域名>       对外访问 IP 或域名（默认自动读取 .env 或本机网卡 IP）
  --repo-dir <DIR>            部署目录（默认: /opt/airport-ai/repo）
  --backup-dir <DIR>          备份存放目录（默认: /opt/airport-ai/backup）

回滚与备份管理选项:
  --list-backups              列出所有可回滚的历史备份时间戳
  --rollback <TIMESTAMP>      一键回滚到指定时间戳的备份（恢复代码、数据库并重新启动）
  --skip-db-restore           回滚时仅恢复代码与容器，不覆盖当前数据库
  --skip-simulators           更新或回滚后不自动批量拉起仿真体
  --admin-user <USER>         用于自动拉起仿真体的管理员账号（默认读取 .env SIM_ADMIN_USERNAME 或 admin）
  --admin-pass <PASS>         用于自动拉起仿真体的管理员密码（默认读取 .env SIM_ADMIN_PASSWORD）

示例:
  sudo bash scripts/docker-update.sh
  sudo bash scripts/docker-update.sh --src /tmp/airport-ai-src.tar.gz --server-ip 192.168.1.100
  sudo bash scripts/docker-update.sh --list-backups
  sudo bash scripts/docker-update.sh --rollback 20261119_163000
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --src)             SRC_ARCHIVE="${2:?缺少 --src 参数}"; shift 2 ;;
      --load-images)     LOAD_IMAGES="${2:?缺少 --load-images 参数}"; shift 2 ;;
      --server-ip)       SERVER_IP="${2:?缺少 --server-ip 参数}"; shift 2 ;;
      --repo-dir)        REPO_DIR="${2:?缺少 --repo-dir 参数}"; shift 2 ;;
      --backup-dir)      BACKUP_ROOT="${2:?缺少 --backup-dir 参数}"; shift 2 ;;
      --list-backups)    LIST_BACKUPS=true; shift ;;
      --rollback)        ROLLBACK_TS="${2:?缺少 --rollback 参数}"; shift 2 ;;
      --skip-db-restore) SKIP_DB_RESTORE=true; shift ;;
      --skip-simulators) SKIP_SIMULATORS=true; shift ;;
      --admin-user)      ADMIN_USER="${2:?缺少 --admin-user 参数}"; shift 2 ;;
      --admin-pass)      ADMIN_PASS="${2:?缺少 --admin-pass 参数}"; shift 2 ;;
      -h|--help)         usage; exit 0 ;;
      *) die "未知参数: $1（使用 --help 查看帮助）" ;;
    esac
  done
}

check_prereqs() {
  [[ ${EUID} -eq 0 ]] || die "请使用 root 或 sudo 权限运行此脚本"
  [[ -d "${REPO_DIR}" ]] || die "未找到部署目录: ${REPO_DIR}（请确认是否已完成首次部署）"
  [[ -f "${REPO_DIR}/.env" ]] || die "未找到环境配置文件: ${REPO_DIR}/.env"
  command -v docker >/dev/null 2>&1 || die "未检测到 docker 命令"
}

detect_server_ip() {
  if [[ -n "${SERVER_IP}" ]]; then
    return
  fi
  # 优先从现有 .env 的 APP_CORS_ALLOWED_ORIGINS 中提取服务器 IP
  local from_env
  from_env="$(grep '^APP_CORS_ALLOWED_ORIGINS=' "${REPO_DIR}/.env" 2>/dev/null \
    | sed -E 's/.*http:\/\/([^,:]+).*/\1/' || true)"
  if [[ -n "${from_env}" && "${from_env}" != "localhost" && "${from_env}" != "127.0.0.1" ]]; then
    SERVER_IP="${from_env}"
  else
    SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
    SERVER_IP="${SERVER_IP:-127.0.0.1}"
  fi
}

list_backups() {
  mkdir -p "${BACKUP_ROOT}"
  log "备份目录: ${BACKUP_ROOT}"
  printf '\n%-20s %-38s %-38s\n' "时间戳 (TIMESTAMP)" "数据库备份文件" "代码目录备份"
  printf '%s\n' "------------------------------------------------------------------------------------------------"
  local found=0
  for repo_bak in $(ls -1dt "${BACKUP_ROOT}"/repo_* 2>/dev/null || true); do
    local ts="${repo_bak##*repo_}"
    local db_bak="${BACKUP_ROOT}/db_${ts}.dump"
    local db_status="无"
    [[ -f "${db_bak}" ]] && db_status="$(basename "${db_bak}") ($(du -h "${db_bak}" | awk '{print $1}'))"
    printf '%-20s %-38s %-38s\n' "${ts}" "${db_status}" "$(basename "${repo_bak}")"
    found=1
  done
  if [[ "${found}" -eq 0 ]]; then
    printf '（暂无历史备份记录）\n'
  fi
  printf '\n'
}

create_backup() {
  local ts="$1"
  mkdir -p "${BACKUP_ROOT}"
  cd "${REPO_DIR}"

  set -a
  # shellcheck disable=SC1090
  source "${REPO_DIR}/.env"
  set +a

  log "[1/5] 备份 PostgreSQL 数据库 -> ${BACKUP_ROOT}/db_${ts}.dump ..."
  if docker compose ps postgres 2>/dev/null | grep -qE "Up|running"; then
    docker compose exec -T postgres pg_dump -U "${DB_USERNAME}" -d "${DB_NAME}" -Fc \
      > "${BACKUP_ROOT}/db_${ts}.dump"
    log "数据库备份完成 ($(du -h "${BACKUP_ROOT}/db_${ts}.dump" | awk '{print $1}'))"
  else
    warn "postgres 容器当前未运行，跳过 pg_dump 在线备份（底层数据卷仍受保护）"
  fi

  log "[2/5] 备份当前运行代码目录与配置 -> ${BACKUP_ROOT}/repo_${ts} ..."
  cp -a "${REPO_DIR}" "${BACKUP_ROOT}/repo_${ts}"

  # 为当前镜像打上备份标签，便于快速回退
  docker tag airport-ai-backend:latest "airport-ai-backend:backup_${ts}" 2>/dev/null || true
  docker tag airport-ai-frontend:latest "airport-ai-frontend:backup_${ts}" 2>/dev/null || true

  # 自动清理超出保留数量的最早备份
  local count=0
  for old_repo in $(ls -1dt "${BACKUP_ROOT}"/repo_* 2>/dev/null || true); do
    count=$((count + 1))
    if (( count > KEEP_BACKUPS )); then
      local old_ts="${old_repo##*repo_}"
      log "清理过期历史备份: ${old_ts}"
      rm -rf "${BACKUP_ROOT}/repo_${old_ts}" "${BACKUP_ROOT}/db_${old_ts}.dump"
      docker rmi "airport-ai-backend:backup_${old_ts}" "airport-ai-frontend:backup_${old_ts}" 2>/dev/null || true
    fi
  done
}

perform_update() {
  check_prereqs
  detect_server_ip

  if [[ -z "${LOAD_IMAGES}" ]]; then
    [[ -f "${SRC_ARCHIVE}" ]] || die "未找到新版本源码包: ${SRC_ARCHIVE}（请先上传或通过 --src 指定路径）"
  else
    [[ -f "${LOAD_IMAGES}" ]] || die "未找到离线镜像包: ${LOAD_IMAGES}"
  fi

  local ts
  ts="$(date +%Y%m%d_%H%M%S)"
  log "============================================================"
  log "开始执行版本更新 (备份时间戳: ${ts})"
  log "部署目录  : ${REPO_DIR}"
  log "服务器地址: ${SERVER_IP}"
  log "============================================================"

  create_backup "${ts}"

  if [[ -f "${SRC_ARCHIVE}" ]]; then
    log "[3/5] 清理旧源码（保留 .env）并解压新版本源码包 ${SRC_ARCHIVE} ..."
    find "${REPO_DIR}" -mindepth 1 -maxdepth 1 ! -name '.env' -exec rm -rf {} +
    tar -xzf "${SRC_ARCHIVE}" -C "${REPO_DIR}"
  else
    log "[3/5] 离线镜像模式：保留当前编排配置..."
  fi

  log "[4/5] 调用 docker-deploy.sh 重新构建并滚动更新容器（保留现有 .env 与数据卷）..."
  cd "${REPO_DIR}"
  if [[ -n "${LOAD_IMAGES}" ]]; then
    bash "${REPO_DIR}/scripts/docker-deploy.sh" --server-ip "${SERVER_IP}" --load-images "${LOAD_IMAGES}"
  else
    bash "${REPO_DIR}/scripts/docker-deploy.sh" --server-ip "${SERVER_IP}"
  fi

  log "[5/5] 清理构建产生的悬空旧镜像并执行更新后验收检查..."
  docker image prune -f >/dev/null 2>&1 || true

  verify_deployment "${ts}"
}

perform_rollback() {
  check_prereqs
  detect_server_ip

  local target_repo="${BACKUP_ROOT}/repo_${ROLLBACK_TS}"
  local target_db="${BACKUP_ROOT}/db_${ROLLBACK_TS}.dump"

  [[ -d "${target_repo}" ]] || die "未找到时间戳为 ${ROLLBACK_TS} 的代码备份目录: ${target_repo}（可执行 --list-backups 查看）"

  log "============================================================"
  log "开始回滚至历史备份版本: ${ROLLBACK_TS}"
  log "============================================================"

  log "[1/3] 恢复代码目录 ${target_repo} -> ${REPO_DIR}（保留当前 .env）..."
  find "${REPO_DIR}" -mindepth 1 -maxdepth 1 ! -name '.env' -exec rm -rf {} +
  cp -a "${target_repo}/." "${REPO_DIR}/"

  cd "${REPO_DIR}"
  set -a
  # shellcheck disable=SC1090
  source "${REPO_DIR}/.env"
  set +a

  if [[ "${SKIP_DB_RESTORE}" != "true" && -f "${target_db}" ]]; then
    log "[2/3] 停止后端容器并还原数据库备份 ${target_db} ..."
    docker compose stop backend || true
    docker compose up -d postgres
    docker compose exec -T postgres pg_restore --clean --if-exists -U "${DB_USERNAME}" -d "${DB_NAME}" \
      < "${target_db}"
  else
    log "[2/3] 跳过数据库还原（未启用或未找到 ${target_db}）"
  fi

  log "[3/3] 重新构建并启动回滚后的容器..."
  if docker image inspect "airport-ai-backend:backup_${ROLLBACK_TS}" >/dev/null 2>&1 \
     && docker image inspect "airport-ai-frontend:backup_${ROLLBACK_TS}" >/dev/null 2>&1; then
    log "检测到备份镜像标签 backup_${ROLLBACK_TS}，直接切换镜像快速启动..."
    docker tag "airport-ai-backend:backup_${ROLLBACK_TS}" airport-ai-backend:latest
    docker tag "airport-ai-frontend:backup_${ROLLBACK_TS}" airport-ai-frontend:latest
    docker compose up -d --no-build
  else
    bash "${REPO_DIR}/scripts/docker-deploy.sh" --server-ip "${SERVER_IP}"
  fi

  verify_deployment "${ROLLBACK_TS}"
}

verify_deployment() {
  local ts="$1"
  cd "${REPO_DIR}"
  set -a
  # shellcheck disable=SC1090
  source "${REPO_DIR}/.env"
  set +a
  local front_port="${FRONTEND_PORT:-80}"

  log "正在检查容器状态与服务健康接口..."
  docker compose ps

  local health_json
  health_json="$(curl -fsS http://127.0.0.1:8080/actuator/health 2>/dev/null || echo '{"status":"DOWN"}')"
  local http_code
  http_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${front_port}/" 2>/dev/null || echo '000')"

  if [[ "${SKIP_SIMULATORS}" != "true" ]] && [[ -f "${REPO_DIR}/scripts/docker-start-simulators.sh" ]]; then
    local sim_pass="${ADMIN_PASS:-${SIM_ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}}"
    if [[ -n "${sim_pass}" ]] || [[ -f "${REPO_DIR}/user.md" ]]; then
      log "正在自动批量拉起容器内所有仿真体设备..."
      local sim_args=()
      [[ -n "${ADMIN_USER}" ]] && sim_args+=(--username "${ADMIN_USER}")
      [[ -n "${sim_pass}" ]] && sim_args+=(--password "${sim_pass}")
      bash "${REPO_DIR}/scripts/docker-start-simulators.sh" "${sim_args[@]}" || warn "部分仿真体自动拉起未完成，可在页面「仿真场景控制」手动启动"
    else
      warn "未在 .env 配置 SIM_ADMIN_PASSWORD 且未传入 --admin-pass，跳过自动拉起仿真体；可随后执行：bash scripts/docker-start-simulators.sh --password <admin密码>"
    fi
  fi

  cat <<EOF

============================================================
  版本更新 / 回滚执行完毕
============================================================
  备份时间戳   : ${ts}
  后端健康状态 : ${health_json}
  前端 HTTP 码 : ${http_code} (http://${SERVER_IP}:${front_port}/)
  数据库备份   : ${BACKUP_ROOT}/db_${ts}.dump
  代码备份目录 : ${BACKUP_ROOT}/repo_${ts}
  一键回滚命令 : sudo bash scripts/docker-update.sh --rollback ${ts}
============================================================
EOF
}

main() {
  parse_args "$@"
  if [[ -z "${SRC_ARCHIVE}" ]]; then
    if [[ -f "/tmp/airport-ai-docker-prebuilt.tar.gz" ]]; then
      SRC_ARCHIVE="/tmp/airport-ai-docker-prebuilt.tar.gz"
    else
      SRC_ARCHIVE="/tmp/airport-ai-src.tar.gz"
    fi
  fi
  if [[ "${LIST_BACKUPS}" == "true" ]]; then
    list_backups
    exit 0
  fi
  if [[ -n "${ROLLBACK_TS}" ]]; then
    perform_rollback
  else
    perform_update
  fi
}

main "$@"
