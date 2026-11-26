# 智慧机场人工智能集群协同服务平台 — Ubuntu 24.04.1 LTS 测试环境部署文档

**适用系统**: Ubuntu 24.04.1 LTS (Noble Numbat) Server (x86_64 / arm64)  
**适用项目**: 智慧机场人工智能集群协同服务平台（`airport-ai-app` + `device-simulator-runtime` + `airport-ai-frontend`）  
**文档用途**: 测试环境单机完整部署（含后端单体应用、PostgreSQL、Redis、Nginx 前端托管及四类设备仿真运行时）

---

## 0. 一键自动化部署（推荐）

仓库已提供针对 Ubuntu 24.04.1 LTS 的幂等一键部署脚本 [deploy-ubuntu24.sh](../scripts/deploy-ubuntu24.sh)，可自动完成基础软件安装、PostgreSQL/Redis 初始化、前后端与仿真器编译、`systemd` 服务注册、Nginx 反向代理配置及健康检查。

将源码上传或克隆到服务器（如 `/opt/airport-ai/repo`）后，执行：

```bash
cd /opt/airport-ai/repo

# 基本用法（自动生成随机 DB/Redis 密码与设备加密密钥）
sudo bash scripts/deploy-ubuntu24.sh --server-ip <服务器IP>

# 若同时配置外部规划模型并开启 UFW 防火墙
sudo bash scripts/deploy-ubuntu24.sh \
  --server-ip <服务器IP> \
  --moonshot-api-key <你的Moonshot_API_Key> \
  --with-ufw
```

常用参数说明（支持重复执行，默认保留已有的 `/etc/airport-ai/airport-ai.env`）：
- `--server-ip <IP/域名>`：写入 CORS 允许列表（不传则自动探测本机 IP）。
- `--moonshot-api-key <KEY>`：配置外部规划模型密钥。
- `--pg-version <15|16>`：默认安装 PostgreSQL 15；若希望直接使用 Ubuntu 24.04 默认源可指定 `16`。
- `--skip-build`：跳过 Maven/npm 构建，直接部署已打包好的 `target/*.jar` 和 `frontend/dist/`。
- `--force-env`：强制重新生成 `/etc/airport-ai/airport-ai.env`。

> 脚本在交互式终端运行时，会在后端就绪后自动调用 `scripts/bootstrap-admin.py` 提示设置管理员初始密码；若需手工分步部署，请继续阅读下文第 1~9 节。

### 方式二：Docker Compose 一键容器化部署（推荐用于快速交付/迁移）

仓库已内置 [docker-compose.yml](../docker-compose.yml)、多阶段镜像构建文件及一键脚本 [docker-deploy.sh](../scripts/docker-deploy.sh)，无需在宿主机手动安装 JDK、Maven、Node.js、PostgreSQL 或 Redis：

```bash
cd /opt/airport-ai/repo
sudo bash scripts/docker-deploy.sh --server-ip <服务器IP> --moonshot-api-key <你的Moonshot_API_Key>
```

如需导出离线镜像包（`.tar.gz`）迁移到无公网环境，可追加 `--export-images ./airport-ai-images.tar.gz`。

---

## 1. 架构与端口规划

### 1.1 部署拓扑

测试环境采用单机部署模式，所有基础中间件与业务服务部署在同一台 Ubuntu 24.04.1 LTS 服务器上：

```text
浏览器 / 测试客户端
        │ HTTP :80
        ▼
┌───────────────────────────────────────────────────────────┐
│                Ubuntu 24.04.1 LTS Server                  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Nginx (:80)                                         │  │
│  │  ├─ /      -> /opt/airport-ai/frontend (静态资源)    │  │
│  │  └─ /api/  -> http://127.0.0.1:8080                 │  │
│  └─────────────────────────────────────────────────────┘  │
│                          │                                │
│                          ▼                                │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 后端单体应用 airport-ai-app (:8080)                  │  │
│  │  Spring Boot 3.2.5 / Java 17 / Flyway (V1~V33)      │  │
│  └───────────┬──────────────────────────┬──────────────┘  │
│              │                          │                 │
│              ▼                          ▼                 │
│  ┌──────────────────────┐   ┌──────────────────────────┐  │
│  │ PostgreSQL (:5432)   │   │ Redis (:6379)            │  │
│  │ 库名: airport_ai     │   │ 会话/缓存管理            │  │
│  └──────────────────────┘   └──────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 设备仿真运行时 device-simulator-runtime              │  │
│  │  - SMART_DISPLAY      :8091 (智慧航显)              │  │
│  │  - BAGGAGE_SCANNER    :8092 (行李测量仪)            │  │
│  │  - FLIGHT_DELAY_BOARD :8093 (航延信息牌)            │  │
│  │  - MOBILE_ROBOT       :8094 (移动引导机器人)        │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
        │ HTTPS (可选，出网)
        ▼
外部规划模型服务（如 Moonshot Kimi / 自定义规划服务）
```

### 1.2 端口清单

| 端口 | 服务 | 监听范围 | 说明 |
|---|---|---|---|
| `80` | Nginx | `0.0.0.0:80` | 测试环境对外统一访问入口（前端页面 + `/api/` 反向代理） |
| `8080` | `airport-ai-app` | `127.0.0.1:8080` 或 `0.0.0.0:8080` | Spring Boot 后端服务；若需本机外直接联调 API 可开放测试网段 |
| `5432` | PostgreSQL | `127.0.0.1:5432` | 关系型数据库，仅本机访问 |
| `6379` | Redis | `127.0.0.1:6379` | 缓存与会话存储，仅本机访问 |
| `8091~8094` | `device-simulator-runtime` | `127.0.0.1:8091~8094` | 四类设备仿真器实例（本机与后端双向 HTTP 通信） |

### 1.3 硬件最低建议（测试环境）

- **CPU**: 4 核及以上
- **内存**: 8 GB 及以上（建议 16 GB，同时运行后端、DB、Redis 及多个仿真器进程更宽裕）
- **磁盘**: 50 GB 及以上可用空间（SSD）

---

## 2. 服务器基础环境准备

以下操作均在 Ubuntu 24.04.1 LTS 服务器终端执行（使用具有 `sudo` 权限的用户）。

### 2.1 更新系统与安装基础工具

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget vim git unzip ca-certificates gnupg lsb-release python3 net-tools
```

### 2.2 设置系统时区

```bash
sudo timedatectl set-timezone Asia/Shanghai
timedatectl
```

### 2.3 配置防火墙（UFW）

若测试服务器启用了 UFW 防火墙，建议仅放行 SSH 和 HTTP（如需外部直接调试 8080 可按需放行）：

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# 若测试期间需要直接访问后端 8080（可选，建议限制来源网段）
# sudo ufw allow from 192.168.0.0/16 to any port 8080 proto tcp

sudo ufw enable
sudo ufw status verbose
```

### 2.4 创建运行用户与目录结构

```bash
# 创建无登录权限的系统运行用户
sudo useradd -r -m -d /opt/airport-ai -s /usr/sbin/nologin airportai || true

# 创建项目运行目录、配置目录与日志目录
sudo mkdir -p /opt/airport-ai/{app,simulator,frontend,logs,repo}
sudo mkdir -p /etc/airport-ai/simulators

# 设置目录属主
sudo chown -R airportai:airportai /opt/airport-ai
```

---

## 3. 基础软件安装（Ubuntu 24.04.1 LTS 适配）

> **注意**：Ubuntu 24.04 已移除 `apt-key`，所有第三方软件源均采用 `/etc/apt/keyrings/` 配合 `signed-by` 方式导入签名密钥。

### 3.1 安装 JDK 17 与 Maven

Ubuntu 24.04 官方源内置 OpenJDK 17 与 Maven：

```bash
sudo apt install -y openjdk-17-jdk maven

# 验证版本
java -version
mvn -version
```

确认 `java -version` 输出为 `17.x`。配置系统级 `JAVA_HOME`（可选，方便脚本调用）：

```bash
JAVA_DIR=$(dirname $(dirname $(readlink -f $(which java))))
echo "export JAVA_HOME=${JAVA_DIR}" | sudo tee /etc/profile.d/java.sh
source /etc/profile.d/java.sh
```

### 3.2 安装 PostgreSQL（15 或 16）

Ubuntu 24.04 默认源提供 PostgreSQL 16（经 Flyway V1~V33 兼容）；若需严格对齐基线版本 **PostgreSQL 15**，可使用 PGDG 官方源安装（二选一，推荐方案 A 同步基线）：

**方案 A：安装 PostgreSQL 15（PGDG 官方源，推荐）**

```bash
sudo install -d /etc/apt/keyrings
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg
echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

sudo apt update
sudo apt install -y postgresql-15 postgresql-contrib-15
```

**方案 B：直接使用 Ubuntu 24.04 默认源 PostgreSQL 16**

```bash
sudo apt install -y postgresql postgresql-contrib
```

启动并验证 PostgreSQL：

```bash
sudo systemctl enable --now postgresql
sudo systemctl status postgresql --no-pager
```

### 3.3 初始化数据库与账号

创建数据库 `airport_ai` 和专用账号 `airportai_user`（请替换为实际测试密码）：

```bash
sudo -u postgres psql << 'EOF'
CREATE DATABASE airport_ai;
CREATE USER airportai_user WITH PASSWORD 'ReplaceWithStrongDbPassword!';
GRANT ALL PRIVILEGES ON DATABASE airport_ai TO airportai_user;
\c airport_ai
GRANT USAGE, CREATE ON SCHEMA public TO airportai_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO airportai_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO airportai_user;
EOF
```

验证数据库连接：

```bash
PGPASSWORD='ReplaceWithStrongDbPassword!' psql -h 127.0.0.1 -U airportai_user -d airport_ai -c "SELECT version();"
```

### 3.4 安装与配置 Redis

Ubuntu 24.04 官方源提供 Redis 7.0.x，也可通过 Redis 官方源安装 7.2+：

```bash
# 使用 Ubuntu 24.04 官方源安装（快速稳定）
sudo apt install -y redis-server
```

> 如需安装 Redis 7.2+ 官方包：
> ```bash
> curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/redis-archive-keyring.gpg
> echo "deb [signed-by=/etc/apt/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
> sudo apt update && sudo apt install -y redis
> ```

修改 Redis 配置 `/etc/redis/redis.conf`（设置内存上限与密码）：

```bash
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.bak

# 建议在 /etc/redis/redis.conf 中确认或调整以下项：
# bind 127.0.0.1 -::1
# requirepass ReplaceWithStrongRedisPassword!
# maxmemory 1gb
# maxmemory-policy allkeys-lru
```

可使用以下命令快速设置（如不设测试密码可跳过 `requirepass` 行）：

```bash
sudo sed -i 's/^# maxmemory <bytes>/maxmemory 1gb/' /etc/redis/redis.conf
sudo sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
echo "requirepass ReplaceWithStrongRedisPassword!" | sudo tee -a /etc/redis/redis.conf
```

重启并验证 Redis：

```bash
sudo systemctl enable --now redis-server
sudo systemctl restart redis-server
redis-cli -a 'ReplaceWithStrongRedisPassword!' ping
# 预期输出: PONG
```

### 3.5 安装 Node.js（用于构建前端）

如果直接在服务器上构建前端，安装 Node.js 20 LTS（NodeSource）：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

> 若已在本地开发机打包好 `frontend/dist/` 并直接上传到服务器，则服务器上可跳过安装 Node.js。

### 3.6 安装 Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable --now nginx
sudo systemctl status nginx --no-pager
```

---

## 4. 拉取源码与编译构建

将项目代码克隆或上传至 `/opt/airport-ai/repo`（以下以 Git 克隆或 `scp` 上传为例）：

```bash
# 示例：将本地源码上传或 git clone 到 /opt/airport-ai/repo
# git clone <仓库地址> /opt/airport-ai/repo
cd /opt/airport-ai/repo
```

### 4.1 构建后端应用（Spring Boot）

```bash
cd /opt/airport-ai/repo/backend
mvn clean package -DskipTests

# 拷贝产物到部署目录
sudo cp target/airport-ai-app-1.0.0.jar /opt/airport-ai/app/
sudo chown -R airportai:airportai /opt/airport-ai/app/
```

### 4.2 构建设备仿真运行时（Simulator）

```bash
cd /opt/airport-ai/repo/simulator
mvn clean package -DskipTests

# 拷贝产物到部署目录
sudo cp target/device-simulator-runtime.jar /opt/airport-ai/simulator/
sudo chown -R airportai:airportai /opt/airport-ai/simulator/
```

### 4.3 构建前端应用（Vue 3 + Vite）

```bash
cd /opt/airport-ai/repo/frontend
npm ci
npm run build

# 拷贝构建产物到 Nginx 静态目录
sudo rm -rf /opt/airport-ai/frontend/*
sudo cp -r dist/* /opt/airport-ai/frontend/
sudo chown -R www-data:www-data /opt/airport-ai/frontend/
```

---

## 5. 后端服务配置与启动

### 5.1 生成设备凭据加密密钥

后端要求配置 `DEVICE_CREDENTIAL_ENCRYPTION_KEY`（建议至少 32 个随机字符）：

```bash
openssl rand -base64 32
```

### 5.2 创建后端环境变量文件

创建 `/etc/airport-ai/airport-ai.env`，严格限制权限为 `0600`（仅 `root` 可读，由 systemd 在启动前注入）：

```bash
sudo tee /etc/airport-ai/airport-ai.env > /dev/null << 'EOF'
# --- 数据库配置 ---
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=airport_ai
DB_USERNAME=airportai_user
DB_PASSWORD=ReplaceWithStrongDbPassword!

# --- Redis 配置 ---
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=ReplaceWithStrongRedisPassword!

# --- 安全与跨域配置 ---
# 请替换为 openssl rand -base64 32 生成的随机字符串
DEVICE_CREDENTIAL_ENCRYPTION_KEY=ReplaceWith32PlusCharsRandomEncryptionKey!
# 若通过服务器 IP 或域名访问，将其加入允许来源列表
APP_CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,http://<服务器IP>
APP_CORS_ALLOW_LOCALHOST_PATTERNS=true

# --- 平台回调与仿真器管理 ---
# 仿真器回调平台的地址（单机部署保持 127.0.0.1:8080 或服务器内网IP:8080）
DEVICE_PLATFORM_BASE_URL=http://127.0.0.1:8080
# 允许平台在“仿真控制”或设备管理侧按需管理仿真 JAR 进程
DEVICE_SIMULATOR_MANAGEMENT_ENABLED=true
DEVICE_SIMULATOR_JAR=/opt/airport-ai/simulator/device-simulator-runtime.jar

# --- 测试环境演示重置开关（按需开启，生产环境必须为 false） ---
DEMO_RESET_ENABLED=true

# --- 外部规划模型配置（二选一） ---
# 方式1：使用 Moonshot (Kimi)
PLANNING_MODEL_PROVIDER=moonshot
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
MOONSHOT_MODEL=kimi-k2.6
MOONSHOT_API_KEY=<你的Moonshot_API_Key>

# 方式2：使用自定义外部规划服务（若使用方式2，请注释方式1并启用下方配置）
# PLANNING_MODEL_PROVIDER=external
# PLANNING_MODEL_ENDPOINT=http://<规划服务地址>
# PLANNING_MODEL_API_KEY=<规划服务Key>
EOF

sudo chmod 600 /etc/airport-ai/airport-ai.env
sudo chown root:root /etc/airport-ai/airport-ai.env
```

> **提示**：请将 `<服务器IP>` 和 `<你的Moonshot_API_Key>` 替换为实际值；若暂不接入外部大模型，可留空 `MOONSHOT_API_KEY`，系统会在模型调用失败时按基线降级规则运行（但真实大模型规划链路不可用）。

### 5.3 创建后端 Systemd 服务

创建 `/etc/systemd/system/airport-ai-app.service`：

```bash
sudo tee /etc/systemd/system/airport-ai-app.service > /dev/null << 'EOF'
[Unit]
Description=Airport AI - Backend Application Service
After=network-online.target postgresql.service redis-server.service
Wants=network-online.target

[Service]
Type=simple
User=airportai
Group=airportai
WorkingDirectory=/opt/airport-ai/app
EnvironmentFile=/etc/airport-ai/airport-ai.env
ExecStart=/usr/bin/java \
  -Xms512m -Xmx2g \
  -Dserver.port=8080 \
  -jar /opt/airport-ai/app/airport-ai-app-1.0.0.jar
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=airport-ai-app

# 安全加固
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
```

### 5.4 启动后端并确认 Flyway 数据库迁移

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now airport-ai-app

# 实时观察启动日志，等待出现 Started AirportAiApplication
sudo journalctl -u airport-ai-app -f
```

启动成功后，验证健康检查接口与 Flyway 迁移版本（应包含 `V1` ~ `V33`）：

```bash
curl -s http://127.0.0.1:8080/actuator/health

PGPASSWORD='ReplaceWithStrongDbPassword!' psql -h 127.0.0.1 -U airportai_user -d airport_ai \
  -c "SELECT version, description, success FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 10;"
```

### 5.5 初始化管理员密码（必做）

Flyway `V3` 初始化的管理员账号默认带有**不可登录的占位密码**。服务首次启动并完成迁移后，使用仓库提供的 `scripts/bootstrap-admin.py` 交互式设置真实密码（该脚本会使用 Spring Security `BCryptPasswordEncoder` 生成哈希并更新数据库）：

```bash
cd /opt/airport-ai/repo
set -a
source /etc/airport-ai/airport-ai.env
set +a

sudo -E python3 scripts/bootstrap-admin.py
```

按提示连续输入两次管理员密码（无回显）即可完成初始化。

---

## 6. 设备仿真运行时部署（测试环境）

平台支持四类设备仿真运行时：`SMART_DISPLAY`、`BAGGAGE_SCANNER`、`FLIGHT_DELAY_BOARD`、`MOBILE_ROBOT`。

> **部署方式说明**：
> - 若在 `airport-ai.env` 中已设置 `DEVICE_SIMULATOR_MANAGEMENT_ENABLED=true` 和 `DEVICE_SIMULATOR_JAR`，后端管理界面可直接拉起/管理仿真器。
> - 若希望在测试服务器以独立守护进程常驻运行 4 台标准仿真设备（推荐用于稳定测试），可按下方 `systemd` 模板服务部署。

### 6.1 创建仿真器 Systemd 模板单元

创建 `/etc/systemd/system/airport-ai-simulator@.service`：

```bash
sudo tee /etc/systemd/system/airport-ai-simulator@.service > /dev/null << 'EOF'
[Unit]
Description=Airport AI Device Simulator (%i)
After=network-online.target airport-ai-app.service
Wants=network-online.target

[Service]
Type=simple
User=airportai
Group=airportai
WorkingDirectory=/opt/airport-ai/simulator
EnvironmentFile=/etc/airport-ai/simulators/%i.env
ExecStart=/usr/bin/java -Xms128m -Xmx256m -jar /opt/airport-ai/simulator/device-simulator-runtime.jar
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

sudo systemctl daemon-reload
```

### 6.2 配置仿真器实例与设备令牌绑定流程

1. 先登录前端页面（或调用接口）在 **设备管理** 中创建/查看对应的 `SIMULATOR` 类型设备档案（接入地址分别对应 `http://127.0.0.1:8091` ~ `8094`）。
2. 在设备管理中点击 **轮换令牌** 获取明文设备 Token（仅显示一次）。
3. 将 Token 写入对应实例的环境文件，例如 `sim-display-001.env`（端口 `8091`）：

```bash
sudo tee /etc/airport-ai/simulators/sim-display-001.env > /dev/null << 'EOF'
SIMULATOR_PORT=8091
SIMULATOR_DEVICE_CODE=SIM_DISPLAY_001
SIMULATOR_DEVICE_TYPE=SIMULATOR
SIMULATED_DEVICE_TYPE=SMART_DISPLAY
SIMULATOR_DEVICE_TOKEN=<从平台轮换获取的设备Token>
SIMULATOR_REPORT_URL=http://127.0.0.1:8080
SIMULATOR_EXECUTION_DELAY_MS=500
SIMULATOR_SCENARIO_RESULT=SUCCESS
SIMULATOR_X=120.5
SIMULATOR_Y=88.2
SIMULATOR_ZONE=T2-B区
EOF

sudo chmod 600 /etc/airport-ai/simulators/sim-display-001.env
sudo chown root:root /etc/airport-ai/simulators/sim-display-001.env
```

其余三类设备可按相同格式创建 `.env`（如 `sim-baggage-001.env` 用 `8092` + `BAGGAGE_SCANNER`、`sim-board-001.env` 用 `8093` + `FLIGHT_DELAY_BOARD`、`sim-robot-001.env` 用 `8094` + `MOBILE_ROBOT`）。

4. 启动仿真器实例并验证健康接口：

```bash
sudo systemctl enable --now airport-ai-simulator@sim-display-001
sudo systemctl status airport-ai-simulator@sim-display-001 --no-pager

# 使用对应设备 Token 验证仿真器健康检查
curl -s -H "Authorization: Bearer <设备Token>" \
  "http://127.0.0.1:8091/device-api/v1/health?nonce=test"
```

5. 回到平台前端 **设备管理** 执行 **连接测试** 并 **创建/绑定代理**，确认设备在线与心跳上报正常。

---

## 7. Nginx 反向代理配置

### 7.1 创建站点配置文件

创建 `/etc/nginx/sites-available/airport-ai`：

```bash
sudo tee /etc/nginx/sites-available/airport-ai > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 20m;

    # 前端静态文件
    location / {
        root /opt/airport-ai/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 REST API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 65s;   # 略大于规划模型 60s 超时配置
    }

    # 预留 WebSocket 代理（当前态势页使用 /api/v1/situation/snapshot 5秒轮询）
    location /ws/ {
        proxy_pass http://127.0.0.1:8080/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 1800s;
        proxy_send_timeout 1800s;
    }

    access_log /var/log/nginx/airport-ai-access.log;
    error_log /var/log/nginx/airport-ai-error.log;
}
EOF
```

### 7.2 启用配置并重载 Nginx

```bash
# 移除默认站点避免端口冲突
sudo rm -f /etc/nginx/sites-enabled/default

# 启用 airport-ai 站点
sudo ln -sf /etc/nginx/sites-available/airport-ai /etc/nginx/sites-enabled/airport-ai

# 检查语法并重载
sudo nginx -t
sudo systemctl reload nginx
```

---

## 8. 部署验收与日常检查

### 8.1 端口与服务状态检查

```bash
# 检查所有关键服务状态
sudo systemctl status postgresql redis-server airport-ai-app nginx --no-pager

# 检查监听端口 (80, 8080, 5432, 6379, 8091...)
ss -tlnp | grep -E ':80\b|:8080\b|:5432\b|:6379\b|:809[1-4]\b'
```

### 8.2 接口与页面冒烟验证

```bash
# 1. 后端健康检查
curl -s http://127.0.0.1:8080/actuator/health

# 2. 通过 Nginx 验证前端首页可达
curl -I http://127.0.0.1/

# 3. 通过 Nginx 验证登录接口
curl -s -X POST http://127.0.0.1/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<你初始化的管理员密码>"}'
```

浏览器访问 `http://<服务器IP>`，使用管理员账号登录，依次确认：
1. 登录成功并进入运行总览。
2. **设备管理** 中设备接入、连接测试与代理心跳正常。
3. **二维态势** 每 5 秒正常刷新设备状态。
4. **仿真控制** 可切换仿真结果场景并下发演示任务。

---

## 9. 常见故障排查

| 现象 | 排查命令 / 原因与处理 |
|---|---|
| 后端启动失败 | `sudo journalctl -u airport-ai-app -n 100 --no-pager`<br>常见原因：PostgreSQL 密码不匹配、Redis 密码错误、`DEVICE_CREDENTIAL_ENCRYPTION_KEY` 未设置或不足长度。 |
| 管理员无法登录 | 确认已运行 `scripts/bootstrap-admin.py` 更新 `V3` 占位密码；注意连续 3 次输错密码会触发锁定，需等待或解锁。 |
| 前端页面 502 Bad Gateway | 检查后端 `8080` 是否启动：`ss -tlnp \| grep 8080`；检查 `/var/log/nginx/airport-ai-error.log`。 |
| 浏览器提示 CORS 跨域错误 | 检查 `/etc/airport-ai/airport-ai.env` 中 `APP_CORS_ALLOWED_ORIGINS` 是否包含当前访问的 `http://<服务器IP>`，修改后执行 `sudo systemctl restart airport-ai-app`。 |
| 任务规划报超时或转基线降级 | 检查 `PLANNING_MODEL_PROVIDER` 与 `MOONSHOT_API_KEY` 配置，以及服务器是否可正常访问 `https://api.moonshot.cn/v1`：`curl -I https://api.moonshot.cn/v1`。 |
| 仿真器设备显示离线 | 检查 `sudo journalctl -u airport-ai-simulator@sim-display-001 -n 50`；确认 `.env` 中 `SIMULATOR_DEVICE_TOKEN` 与平台轮换生成的 Token 一致，且 `SIMULATOR_REPORT_URL` 可达。 |
