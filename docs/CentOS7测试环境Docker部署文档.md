# 智慧机场人工智能集群协同服务平台 — CentOS 7 测试环境 Docker 一键部署文档

**适用系统**: CentOS 7.x (x86_64，可连接外网)  
**部署方式**: Docker Compose 容器化一键部署  
**包含组件**: PostgreSQL 15 + Redis 7.2 + 后端单体应用（含设备仿真运行时 `device-simulator-runtime`）+ Nginx 前端托管  
**预置数据**: Flyway `V1~V33` 数据库迁移 + 最新版 F2 标准演示数据集（`F2-DEMO-20261118`）

---

## 1. 本地打包与上传（Windows 本机操作）

在 Windows 本机项目根目录执行以下命令打包精简源码（自动排除 `node_modules`、`target`、`.git` 等冗余目录）：

```powershell
mkdir -Force outputs | Out-Null
tar --exclude=.git --exclude=node_modules --exclude=target --exclude=.local-test --exclude=document --exclude=acceptance --exclude=outputs -czf outputs\airport-ai-src.tar.gz .
```

将压缩包上传到 CentOS 7 服务器：

```powershell
scp outputs\airport-ai-src.tar.gz root@<服务器IP>:/tmp/
```

---

## 2. CentOS 7 服务器一键部署

以下操作在 CentOS 7 服务器终端中执行（需 `root` 或 `sudo` 权限）。

### 2.1 解压部署包

```bash
mkdir -p /opt/airport-ai/repo
tar -xzf /tmp/airport-ai-src.tar.gz -C /opt/airport-ai/repo
cd /opt/airport-ai/repo
```

### 2.2 执行一键自动化部署脚本

```bash
# 标准一键部署（自动安装 Docker/Compose、生成 .env 随机密钥、构建并启动全部服务）
sudo bash scripts/docker-deploy.sh --server-ip <服务器IP> --moonshot-api-key <你的Moonshot_API_Key>
```

> **可选参数说明**：
> - 若暂不接入 Moonshot 规划模型，可省略 `--moonshot-api-key`（系统将按基线降级逻辑运行，但大模型智能规划功能不可用）。
> - 若希望部署完成后顺便导出离线镜像包供其他内网机器使用，可追加：
>   ```bash
>   --export-images ./airport-ai-images.tar.gz
>   ```
> - 若需自定义前端访问端口（默认 `80`），可追加 `--frontend-port 8088`。

### 2.3 脚本自动执行内容说明

`scripts/docker-deploy.sh` 会依次完成以下步骤：
1. **自动修复 CentOS 7 软件源与安装 Docker**：检测到 `mirrorlist.centos.org` 失效时自动切换为 `vault.centos.org`，安装 `docker-ce` 与 `docker-compose-plugin` 并启用开机自启。
2. **生成环境配置 `.env`**：自动生成强随机数据库密码、Redis 密码及 32 位以上 `DEVICE_CREDENTIAL_ENCRYPTION_KEY`，设置 `DEMO_RESET_ENABLED=true`，并自动配置 `APP_CORS_ALLOWED_ORIGINS`。
3. **多阶段构建并启动容器**：
   - `airport-ai-postgres`（PostgreSQL 15，数据持久化于 `postgres_data` 卷）
   - `airport-ai-redis`（Redis 7.2，持久化于 `redis_data` 卷）
   - `airport-ai-backend`（JDK 17 + `airport-ai-app.jar` + `device-simulator-runtime.jar`，自动执行 Flyway `V1~V33`）
   - `airport-ai-frontend`（Nginx 1.27 静态托管 + `/api/` 反向代理）
4. **交互式初始化管理员密码**：
   后端健康检查通过后，脚本检测到 `admin` 仍为占位密码时，会提示输入 12 位以上管理员初始密码（输入无回显，连续确认两次）。

---

## 3. 防火墙放行（若服务器开启了 firewalld）

检查防火墙状态并放行 HTTP 访问端口（默认 `80`）：

```bash
# 查看 firewalld 是否运行
sudo systemctl status firewalld --no-pager

# 若正在运行，放行 80 端口（如修改了前端端口请同步放行对应端口）
sudo firewall-cmd --permanent --add-service=http
# 如需从外部直接调试后端 8080 接口（可选）
# sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

---

## 4. 部署验收与测试数据准备

### 4.1 检查容器与健康状态

```bash
cd /opt/airport-ai/repo

# 查看所有容器运行与健康状态（均应为 Up / healthy）
docker compose ps

# 验证后端健康检查接口
curl -s http://127.0.0.1:8080/actuator/health

# 验证前端入口可达
curl -I http://127.0.0.1/
```

### 4.2 登录与恢复标准测试数据集

1. 浏览器访问：`http://<服务器IP>/`
2. 使用管理员账号 `admin` 及部署时设置的初始密码登录。
3. **恢复 F2 标准测试数据集**（`F2-DEMO-20261118`）：
   - 进入系统的 **演示数据重置** 页面，输入确认短语 `恢复F2标准演示数据` 执行重置。
   - 重置后将自动写入 **6 台 F2 仿真设备**、**3 套最新基线模板** 与 **3 类核心任务场景定义**。
4. **启动设备仿真运行时**：
   - 因为后端镜像已内置 `/app/device-simulator-runtime.jar` 且开启了 `DEVICE_SIMULATOR_MANAGEMENT_ENABLED=true`，直接在平台 **设备管理 / 仿真控制** 界面即可配置或拉起仿真设备开始联调测试。

---

## 5. 离线镜像导出与新服务器复用（可选）

如果后续需要将当前环境快速复制到其他无法联网的 CentOS 7 / Ubuntu 服务器：

1. **在当前服务器导出完整镜像包**：
   ```bash
   cd /opt/airport-ai/repo
   docker save airport-ai-backend:latest airport-ai-frontend:latest postgres:15-alpine redis:7.2-alpine \
     | gzip > airport-ai-images.tar.gz
   ```
2. **在新服务器上导入并一键启动（免源码编译）**：
   将 `airport-ai-images.tar.gz`、`docker-compose.yml` 和 `scripts/docker-deploy.sh` 拷贝到新服务器同一目录后执行：
   ```bash
   sudo bash scripts/docker-deploy.sh \
     --server-ip <新服务器IP> \
     --load-images ./airport-ai-images.tar.gz
   ```

---

## 6. 日常运维与故障排查命令

| 操作 | 命令 |
|---|---|
| 查看后端实时日志 | `cd /opt/airport-ai/repo && docker compose logs -f backend` |
| 查看全部容器日志 | `cd /opt/airport-ai/repo && docker compose logs -f --tail=100` |
| 重启后端服务（修改 `.env` 后） | `cd /opt/airport-ai/repo && docker compose up -d backend` |
| 停止全部服务（保留数据库数据） | `cd /opt/airport-ai/repo && docker compose down` |
| 彻底清空数据并重新初始化 | `cd /opt/airport-ai/repo && docker compose down -v && docker compose up -d` |
| 进入 PostgreSQL 命令行 | `cd /opt/airport-ai/repo && source .env && docker compose exec postgres psql -U "$DB_USERNAME" -d "$DB_NAME"` |
| 手动补充初始化管理员密码 | `cd /opt/airport-ai/repo && docker compose exec backend java -cp '/app/bootstrap:/app/bootstrap/*' PasswordHash /tmp/admin.hash` |

### 常见问题
- **页面提示 CORS 跨域错误**：检查 `/opt/airport-ai/repo/.env` 中的 `APP_CORS_ALLOWED_ORIGINS` 是否包含当前浏览器访问的 `http://<服务器IP>`（含端口，如有），修改后执行 `docker compose up -d backend` 生效。
- **规划任务报超时或转入基线降级**：检查 `.env` 中的 `MOONSHOT_API_KEY` 是否正确配置，以及服务器是否可正常访问 `https://api.moonshot.cn/v1`（`curl -I https://api.moonshot.cn/v1`）。
- **重新部署更新代码**：上传新源码包覆盖 `/opt/airport-ai/repo` 后，再次执行 `sudo bash scripts/docker-deploy.sh --server-ip <服务器IP>`（脚本会保留已有 `.env` 与数据库卷数据，仅重新构建并更新容器）。
