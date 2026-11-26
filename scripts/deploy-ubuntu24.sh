#!/usr/bin/env bash
# 一键自动化部署脚本：Ubuntu 24.04.1 LTS 测试环境
# 适用项目：智慧机场人工智能集群协同服务平台
# 用法示例：
#   sudo bash scripts/deploy-ubuntu24.sh --server-ip 192.168.1.100 --moonshot-api-key sk-xxx
#   sudo bash scripts/deploy-ubuntu24.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_ROOT="/opt/airport-ai"
ETC_DIR="/etc/airport-ai"
ENV_FILE="${ETC_DIR}/airport-ai.env"

SERVER_IP=""
MOONSHOT_API_KEY="${MOONSHOT_API_KEY:-}"
DEMO_RESET_ENABLED="${DEMO_RESET_ENABLED:-true}"
PG_VERSION="${PG_VERSION:-15}"
SKIP_BUILD=false
WITH_UFW=false
FORCE_ENV=false

log()  { printf '[INFO] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
die()  { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
用法: sudo bash $0 [选项]

选项:
  --server-ip <IP/域名>       对外访问 IP 或域名（用于 CORS 配置，默认自动探测本机 IP）
  --moonshot-api-key <KEY>    外部规划模型 Moonshot API Key（可选，不传则留空）
  --pg-version <15|16>        PostgreSQL 主版本（默认: 15；选 16 则使用 Ubuntu 24.04 默认源）
  --demo-reset <true|false>   是否开启演示重置接口（默认: true）
  --repo-dir <PATH>           源码根目录（默认: 脚本所在仓库根目录 ${REPO_DIR}）
  --skip-build                跳过 Maven/npm 构建，直接部署已存在的 target/ 和 dist/
  --with-ufw                  自动配置并启用 UFW 防火墙（放行 22/80/443）
  --force-env                 强制重新生成 ${ENV_FILE}（默认保留已有环境文件）
  -h, --help                  显示帮助信息
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --server-ip)        SERVER_IP="${2:?缺少 --server-ip 参数}"; shift 2 ;;
      --moonshot-api-key) MOONSHOT_API_KEY="${2:?缺少 --moonshot-api-key 参数}"; shift 2 ;;
      --pg-version)       PG_VERSION="${2:?缺少 --pg-version 参数}"; shift 2 ;;
      --demo-reset)       DEMO_RESET_ENABLED="${2:?缺少 --demo-reset 参数}"; shift 2 ;;
      --repo-dir)         REPO_DIR="$(cd "${2:?缺少 --repo-dir 参数}" && pwd)"; shift 2 ;;
      --skip-build)       SKIP_BUILD=true; shift ;;
      --with-ufw)         WITH_UFW=true; shift ;;
      --force-env)        FORCE_ENV=true; shift ;;
      -h|--help)          usage; exit 0 ;;
      *) die "未知参数: $1（使用 --help 查看说明）" ;;
    esac
  done
}

check_environment() {
  [[ ${EUID} -eq 0 ]] || die "请使用 root 或 sudo 运行此脚本"
  [[ -f /etc/os-release ]] || die "无法检测操作系统版本"
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != 24.04* ]]; then
    warn "当前系统为 ${PRETTY_NAME:-unknown}，本脚本针对 Ubuntu 24.04.x LTS 验证，继续执行可能存在软件源差异。"
  fi
  if [[ -z "${SERVER_IP}" ]]; then
    SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
    SERVER_IP="${SERVER_IP:-127.0.0.1}"
  fi
  log "部署源码目录: ${REPO_DIR}"
  log "服务器访问地址: ${SERVER_IP}"
}

install_base_packages() {
  log "更新系统软件源并安装基础依赖..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y \
    curl wget vim git unzip ca-certificates gnupg lsb-release \
    python3 net-tools openssl openjdk-17-jdk maven nginx redis-server

  timedatectl set-timezone Asia/Shanghai || true
}

install_postgresql() {
  if command -v psql >/dev/null 2>&1; then
    log "检测到已安装 PostgreSQL: $(psql --version)"
  elif [[ "${PG_VERSION}" == "15" ]]; then
    log "添加 PGDG 官方源并安装 PostgreSQL 15..."
    install -d /etc/apt/keyrings
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      | gpg --dearmor --yes -o /etc/apt/keyrings/postgresql.gpg
    echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list
    apt-get update -y
    apt-get install -y postgresql-15 postgresql-contrib-15
  else
    log "安装 Ubuntu 默认源 PostgreSQL..."
    apt-get install -y postgresql postgresql-contrib
  fi
  systemctl enable --now postgresql
}

install_nodejs() {
  if [[ "${SKIP_BUILD}" == "true" ]]; then
    return
  fi
  if command -v node >/dev/null 2>&1; then
    local major
    major="$(node -v | sed -E 's/^v([0-9]+).*/\1/')"
    if [[ "${major}" -ge 18 ]]; then
      log "检测到已安装 Node.js $(node -v)"
      return
    fi
  fi
  log "安装 Node.js 20 LTS..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
}

setup_users_and_dirs() {
  log "创建系统用户 airportai 与部署目录..."
  id -u airportai >/dev/null 2>&1 || useradd -r -m -d "${APP_ROOT}" -s /usr/sbin/nologin airportai
  mkdir -p "${APP_ROOT}"/{app,simulator,frontend,logs} "${ETC_DIR}/simulators"
  chown -R airportai:airportai "${APP_ROOT}"
}

generate_secret() {
  openssl rand -hex 24
}

prepare_env_file() {
  if [[ -f "${ENV_FILE}" && "${FORCE_ENV}" != "true" ]]; then
    log "检测到已有 ${ENV_FILE}，保留现有配置与密钥（如需覆盖请加 --force-env）"
    return
  fi

  log "生成后端环境配置文件 ${ENV_FILE}..."
  local db_pass redis_pass enc_key cors_origins
  db_pass="${DB_PASSWORD:-$(generate_secret)}"
  redis_pass="${REDIS_PASSWORD:-$(generate_secret)}"
  enc_key="${DEVICE_CREDENTIAL_ENCRYPTION_KEY:-$(openssl rand -base64 32 | tr -d '\n')}"
  cors_origins="http://localhost,http://127.0.0.1,http://${SERVER_IP}"

  cat > "${ENV_FILE}" <<EOF
# 由 scripts/deploy-ubuntu24.sh 自动生成
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=airport_ai
DB_USERNAME=airportai_user
DB_PASSWORD=${db_pass}

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=${redis_pass}

DEVICE_CREDENTIAL_ENCRYPTION_KEY=${enc_key}
APP_CORS_ALLOWED_ORIGINS=${cors_origins}
APP_CORS_ALLOW_LOCALHOST_PATTERNS=true

DEVICE_PLATFORM_BASE_URL=http://127.0.0.1:8080
DEVICE_SIMULATOR_MANAGEMENT_ENABLED=true
DEVICE_SIMULATOR_JAR=${APP_ROOT}/simulator/device-simulator-runtime.jar

DEMO_RESET_ENABLED=${DEMO_RESET_ENABLED}

PLANNING_MODEL_PROVIDER=moonshot
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
MOONSHOT_MODEL=kimi-k2.6
MOONSHOT_API_KEY=${MOONSHOT_API_KEY}
EOF

  chmod 600 "${ENV_FILE}"
  chown root:root "${ENV_FILE}"
}

load_env_file() {
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
}

configure_postgresql() {
  log "初始化 PostgreSQL 数据库 (${DB_NAME}) 与用户 (${DB_USERNAME})..."
  local user_exists db_exists
  user_exists="$(su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${DB_USERNAME}'\"")"
  if [[ "${user_exists}" != "1" ]]; then
    su - postgres -c "psql -v ON_ERROR_STOP=1 -c \"CREATE USER ${DB_USERNAME} WITH PASSWORD '${DB_PASSWORD}';\""
  else
    su - postgres -c "psql -v ON_ERROR_STOP=1 -c \"ALTER USER ${DB_USERNAME} WITH PASSWORD '${DB_PASSWORD}';\""
  fi

  db_exists="$(su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\"")"
  if [[ "${db_exists}" != "1" ]]; then
    su - postgres -c "psql -v ON_ERROR_STOP=1 -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USERNAME};\""
  fi

  su - postgres -c "psql -v ON_ERROR_STOP=1 -d ${DB_NAME}" <<EOF
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USERNAME};
GRANT USAGE, CREATE ON SCHEMA public TO ${DB_USERNAME};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USERNAME};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USERNAME};
EOF
}

configure_redis() {
  log "配置 Redis 内存策略与访问密码..."
  local conf="/etc/redis/redis.conf"
  [[ -f "${conf}.bak" ]] || cp "${conf}" "${conf}.bak"

  sed -i 's/^# maxmemory <bytes>/maxmemory 1gb/' "${conf}"
  sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' "${conf}"
  if grep -qE '^[# ]*requirepass ' "${conf}"; then
    sed -i "s|^[# ]*requirepass .*|requirepass ${REDIS_PASSWORD}|" "${conf}"
  else
    echo "requirepass ${REDIS_PASSWORD}" >> "${conf}"
  fi

  systemctl enable --now redis-server
  systemctl restart redis-server
  redis-cli -a "${REDIS_PASSWORD}" --no-auth-warning ping | grep -q "PONG" || die "Redis 连通性校验失败"
}

build_and_deploy_artifacts() {
  if [[ "${SKIP_BUILD}" != "true" ]]; then
    log "编译后端应用..."
    mvn -f "${REPO_DIR}/backend/pom.xml" clean package -DskipTests
    log "编译设备仿真运行时..."
    mvn -f "${REPO_DIR}/simulator/pom.xml" clean package -DskipTests
    log "构建前端静态资源..."
    (cd "${REPO_DIR}/frontend" && npm ci && npm run build)
  fi

  local backend_jar="${REPO_DIR}/backend/target/airport-ai-app-1.0.0.jar"
  local sim_jar="${REPO_DIR}/simulator/target/device-simulator-runtime.jar"
  local front_dist="${REPO_DIR}/frontend/dist"

  [[ -f "${backend_jar}" ]] || die "未找到后端 JAR: ${backend_jar}"
  [[ -f "${sim_jar}" ]]     || die "未找到仿真器 JAR: ${sim_jar}"
  [[ -d "${front_dist}" ]]  || die "未找到前端构建目录: ${front_dist}"

  cp "${backend_jar}" "${APP_ROOT}/app/"
  cp "${sim_jar}" "${APP_ROOT}/simulator/"
  chown -R airportai:airportai "${APP_ROOT}/app" "${APP_ROOT}/simulator"

  rm -rf "${APP_ROOT}/frontend/"*
  cp -r "${front_dist}/"* "${APP_ROOT}/frontend/"
  chown -R www-data:www-data "${APP_ROOT}/frontend"
}

install_systemd_units() {
  log "安装 systemd 服务单元..."
  cat > /etc/systemd/system/airport-ai-app.service <<EOF
[Unit]
Description=Airport AI - Backend Application Service
After=network-online.target postgresql.service redis-server.service
Wants=network-online.target

[Service]
Type=simple
User=airportai
Group=airportai
WorkingDirectory=${APP_ROOT}/app
EnvironmentFile=${ENV_FILE}
ExecStart=/usr/bin/java -Xms512m -Xmx2g -Dserver.port=8080 -jar ${APP_ROOT}/app/airport-ai-app-1.0.0.jar
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=airport-ai-app
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

  cat > /etc/systemd/system/airport-ai-simulator@.service <<EOF
[Unit]
Description=Airport AI Device Simulator (%i)
After=network-online.target airport-ai-app.service
Wants=network-online.target

[Service]
Type=simple
User=airportai
Group=airportai
WorkingDirectory=${APP_ROOT}/simulator
EnvironmentFile=${ETC_DIR}/simulators/%i.env
ExecStart=/usr/bin/java -Xms128m -Xmx256m -jar ${APP_ROOT}/simulator/device-simulator-runtime.jar
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=airport-ai-sim-%i
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
}

configure_nginx() {
  log "配置 Nginx 反向代理..."
  cat > /etc/nginx/sites-available/airport-ai <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 20m;

    location / {
        root ${APP_ROOT}/frontend;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 65s;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8080/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 1800s;
        proxy_send_timeout 1800s;
    }

    access_log /var/log/nginx/airport-ai-access.log;
    error_log /var/log/nginx/airport-ai-error.log;
}
EOF

  rm -f /etc/nginx/sites-enabled/default
  ln -sf /etc/nginx/sites-available/airport-ai /etc/nginx/sites-enabled/airport-ai
  nginx -t
  systemctl enable --now nginx
  systemctl reload nginx
}

configure_ufw() {
  if [[ "${WITH_UFW}" != "true" ]]; then
    return
  fi
  log "配置 UFW 防火墙..."
  apt-get install -y ufw
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable
}

start_and_wait_backend() {
  log "启动 airport-ai-app 并等待健康检查就绪..."
  systemctl enable airport-ai-app
  systemctl restart airport-ai-app

  local deadline=$((SECONDS + 90))
  while (( SECONDS < deadline )); do
    if curl -fsS http://127.0.0.1:8080/actuator/health 2>/dev/null | grep -q '"status":"UP"'; then
      log "后端服务健康检查通过 (UP)"
      return
    fi
    sleep 2
  done
  journalctl -u airport-ai-app -n 60 --no-pager >&2
  die "后端服务未在 90 秒内就绪，请检查上方日志"
}

maybe_bootstrap_admin() {
  local placeholder_count
  placeholder_count="$(PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USERNAME}" -d "${DB_NAME}" \
    -tAc "SELECT COUNT(*) FROM users WHERE username = 'admin' AND password_hash LIKE '%PLACEHOLDER%';")"
  if [[ "${placeholder_count}" == "0" ]]; then
    log "管理员密码已初始化，跳过 bootstrap-admin.py"
    return
  fi

  if [[ -t 0 ]]; then
    log "检测到管理员仍为占位密码，启动交互式密码初始化..."
    python3 "${REPO_DIR}/scripts/bootstrap-admin.py"
  else
    warn "当前非交互终端，请部署完成后手动执行以下命令初始化管理员密码："
    printf '  sudo bash -c "set -a; source %s; set +a; python3 %s/scripts/bootstrap-admin.py"\n' "${ENV_FILE}" "${REPO_DIR}"
  fi
}

print_summary() {
  cat <<EOF

============================================================
  Ubuntu 24.04.1 LTS 测试环境部署完成
============================================================
  前端访问地址 : http://${SERVER_IP}/
  后端健康检查 : http://127.0.0.1:8080/actuator/health
  环境配置文件 : ${ENV_FILE} (权限 0600，内含 DB/Redis/加密密钥)
  后端服务日志 : sudo journalctl -u airport-ai-app -f
  仿真器部署   : 参见 docs/Ubuntu24.04测试环境部署文档.md 第 6 节
============================================================
EOF
}

main() {
  parse_args "$@"
  check_environment
  install_base_packages
  install_postgresql
  install_nodejs
  setup_users_and_dirs
  prepare_env_file
  load_env_file
  configure_postgresql
  configure_redis
  build_and_deploy_artifacts
  install_systemd_units
  configure_nginx
  configure_ufw
  start_and_wait_backend
  maybe_bootstrap_admin
  print_summary
}

main "$@"
