#!/usr/bin/env bash
# Docker Compose 一键构建与自动化部署脚本（支持 CentOS 7 / Ubuntu 24.04）
# 用法示例：
#   sudo bash scripts/docker-deploy.sh --server-ip 192.168.1.100 --moonshot-api-key sk-xxx
#   sudo bash scripts/docker-deploy.sh --export-images ./airport-ai-images.tar.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_DIR}/.env"

SERVER_IP=""
MOONSHOT_API_KEY="${MOONSHOT_API_KEY:-}"
FRONTEND_PORT="${FRONTEND_PORT:-80}"
FORCE_ENV=false
EXPORT_PATH=""
LOAD_PATH=""

log()  { printf '[INFO] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
die()  { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
用法: sudo bash $0 [选项]

选项:
  --server-ip <IP/域名>       对外访问 IP 或域名（写入 CORS，默认自动探测本机 IP）
  --moonshot-api-key <KEY>    外部规划模型 Moonshot API Key（可选）
  --frontend-port <PORT>      前端暴露端口（默认: 80）
  --force-env                 强制重新生成 .env（默认保留已有 .env）
  --export-images <TAR.GZ>    构建后额外导出离线镜像包（用于离线服务器导入）
  --load-images <TAR.GZ>      从离线镜像包导入镜像并直接启动（跳过源码构建）
  -h, --help                  显示帮助信息
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --server-ip)        SERVER_IP="${2:?缺少 --server-ip 参数}"; shift 2 ;;
      --moonshot-api-key) MOONSHOT_API_KEY="${2:?缺少 --moonshot-api-key 参数}"; shift 2 ;;
      --frontend-port)    FRONTEND_PORT="${2:?缺少 --frontend-port 参数}"; shift 2 ;;
      --force-env)        FORCE_ENV=true; shift ;;
      --export-images)    EXPORT_PATH="${2:?缺少 --export-images 参数}"; shift 2 ;;
      --load-images)      LOAD_PATH="${2:?缺少 --load-images 参数}"; shift 2 ;;
      -h|--help)          usage; exit 0 ;;
      *) die "未知参数: $1" ;;
    esac
  done
}

install_docker_ubuntu() {
  log "正在为 Ubuntu/Debian 安装 Docker Engine 与 Compose 插件..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg openssl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  # shellcheck disable=SC1091
  source /etc/os-release
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_docker_centos7() {
  log "正在为 CentOS 7 安装 Docker Engine 与 Compose 插件..."
  # CentOS 7 已 EOL，若仍指向失效的 mirrorlist.centos.org 则自动切换为 vault.centos.org
  if grep -q 'mirrorlist.centos.org' /etc/yum.repos.d/CentOS-*.repo 2>/dev/null; then
    log "检测到 CentOS 7 默认镜像源已停服，自动切换至 vault.centos.org..."
    sed -i 's/mirrorlist=/#mirrorlist=/g' /etc/yum.repos.d/CentOS-*.repo
    sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-*.repo
  fi
  yum install -y yum-utils curl openssl
  yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
  yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_docker_if_missing() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "检测到已安装 Docker 与 Docker Compose"
    return
  fi
  [[ ${EUID} -eq 0 ]] || die "安装 Docker 需要 root/sudo 权限"
  # shellcheck disable=SC1091
  [[ -f /etc/os-release ]] && source /etc/os-release
  case "${ID:-}" in
    ubuntu|debian) install_docker_ubuntu ;;
    centos|rhel)   install_docker_centos7 ;;
    *) die "暂不支持自动安装 Docker 的系统: ${ID:-unknown}，请先手动安装 Docker 与 docker-compose-plugin 后重试" ;;
  esac
  systemctl enable --now docker
}

prepare_env() {
  if [[ -z "${SERVER_IP}" ]]; then
    SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
    SERVER_IP="${SERVER_IP:-127.0.0.1}"
  fi

  if [[ -f "${ENV_FILE}" && "${FORCE_ENV}" != "true" ]]; then
    log "检测到已有 ${ENV_FILE}，保留现有配置（如需重置请加 --force-env）"
    return
  fi

  log "生成 Docker Compose 环境文件 ${ENV_FILE}..."
  local db_pass redis_pass enc_key
  db_pass="$(openssl rand -hex 20)"
  redis_pass="$(openssl rand -hex 20)"
  enc_key="$(openssl rand -base64 32 | tr -d '\n')"

  cat > "${ENV_FILE}" <<EOF
FRONTEND_PORT=${FRONTEND_PORT}
BACKEND_PORT=8080

DB_NAME=airport_ai
DB_USERNAME=airportai_user
DB_PASSWORD=${db_pass}

REDIS_PASSWORD=${redis_pass}

DEVICE_CREDENTIAL_ENCRYPTION_KEY=${enc_key}
APP_CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,http://${SERVER_IP},http://${SERVER_IP}:${FRONTEND_PORT}
APP_CORS_ALLOW_LOCALHOST_PATTERNS=true

DEMO_RESET_ENABLED=true

PLANNING_MODEL_PROVIDER=moonshot
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
MOONSHOT_MODEL=kimi-k2.6
MOONSHOT_API_KEY=${MOONSHOT_API_KEY}
EOF
  chmod 600 "${ENV_FILE}"
}

build_and_up() {
  cd "${REPO_DIR}"
  if [[ -n "${LOAD_PATH}" ]]; then
    [[ -f "${LOAD_PATH}" ]] || die "未找到离线镜像包: ${LOAD_PATH}"
    log "正在从离线镜像包 ${LOAD_PATH} 导入镜像..."
    docker load -i "${LOAD_PATH}"
    log "跳过源码编译，直接使用离线镜像启动全部容器..."
    docker compose up -d --no-build
  else
    if [[ -f "${REPO_DIR}/prebuilt/airport-ai-app.jar" ]] \
       && [[ -f "${REPO_DIR}/prebuilt/device-simulator-runtime.jar" ]] \
       && [[ -f "${REPO_DIR}/prebuilt/frontend-dist/index.html" ]] \
       && [[ -f "${REPO_DIR}/docker/backend/Dockerfile.prebuilt" ]] \
       && [[ -f "${REPO_DIR}/docker/frontend/Dockerfile.prebuilt" ]]; then
      log "检测到预编译成品目录 prebuilt/，跳过 Maven/npm 依赖下载与编译，直接打包镜像..."
      export BACKEND_DOCKERFILE="docker/backend/Dockerfile.prebuilt"
      export FRONTEND_DOCKERFILE="docker/frontend/Dockerfile.prebuilt"
    else
      log "开始构建最新镜像并启动全部容器..."
    fi
    docker compose up -d --build
  fi

  if [[ -n "${EXPORT_PATH}" ]]; then
    log "正在导出镜像到 ${EXPORT_PATH}..."
    docker save airport-ai-backend:latest airport-ai-frontend:latest postgres:15-alpine redis:7.2-alpine \
      | gzip > "${EXPORT_PATH}"
    log "离线镜像导出完成: ${EXPORT_PATH}"
  fi
}

wait_for_backend() {
  cd "${REPO_DIR}"
  log "等待后端健康检查通过（Flyway V1~V33 自动迁移中）..."
  local deadline=$((SECONDS + 120))
  while (( SECONDS < deadline )); do
    if docker compose ps --format json 2>/dev/null | grep -q '"Health":"healthy"' \
       && curl -fsS http://127.0.0.1:8080/actuator/health 2>/dev/null | grep -q '"status":"UP"'; then
      log "后端服务已就绪 (UP)"
      return
    fi
    sleep 3
  done
  docker compose logs --tail=60 backend >&2
  die "后端服务未在 120 秒内就绪"
}

bootstrap_admin_if_needed() {
  cd "${REPO_DIR}"
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  local count
  count="$(docker compose exec -T postgres psql -U "${DB_USERNAME}" -d "${DB_NAME}" -tAc \
    "SELECT COUNT(*) FROM users WHERE username='admin' AND password_hash LIKE '%PLACEHOLDER%';")"
  if [[ "${count}" == "0" ]]; then
    log "管理员密码已初始化，跳过设置"
    return
  fi

  if [[ -t 0 ]]; then
    log "检测到管理员仍为占位密码，请输入初始管理员密码（12位以上，无回显）："
    docker compose exec backend java -cp '/app/bootstrap:/app/bootstrap/*' PasswordHash /tmp/admin.hash
    local hash
    hash="$(docker compose exec -T backend cat /tmp/admin.hash)"
    docker compose exec -T backend rm -f /tmp/admin.hash
    docker compose exec -T postgres psql -U "${DB_USERNAME}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 \
      -c "UPDATE users SET password_hash='${hash}' WHERE username='admin' AND password_hash LIKE '%PLACEHOLDER%';"
    log "管理员密码初始化完成！"
  else
    warn "非交互终端，请部署后执行交互式初始化或查看 docker-compose 状态"
  fi
}

main() {
  parse_args "$@"
  install_docker_if_missing
  prepare_env
  build_and_up
  wait_for_backend
  bootstrap_admin_if_needed

  cat <<EOF

============================================================
  Docker Compose 一键部署完成
============================================================
  前端访问地址 : http://${SERVER_IP}:${FRONTEND_PORT}/
  后端健康检查 : http://127.0.0.1:8080/actuator/health
  查看日志     : docker compose logs -f backend
  停止服务     : docker compose down
============================================================
EOF
}

main "$@"
