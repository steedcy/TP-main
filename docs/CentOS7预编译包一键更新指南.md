# CentOS 7 预编译包一键更新指南

本指南适用于使用本机预编译部署包（`outputs/airport-ai-docker-prebuilt.tar.gz`）对 CentOS 7 测试服务器进行免依赖、全自动版本更新与仿真体拉起。

> **配套脚本与完整手册**：
> - 本机预编译打包脚本：[scripts/package-docker-prebuilt.ps1](../scripts/package-docker-prebuilt.ps1)
> - 服务器一键更新脚本：[scripts/docker-update.sh](../scripts/docker-update.sh)
> - 仿真体批量拉起脚本：[scripts/docker-start-simulators.sh](../scripts/docker-start-simulators.sh)
> - 完整更新与回滚手册：[测试服务器版本更新部署手册.md](./测试服务器版本更新部署手册.md)

---

## 1. 本机生成预编译包（Windows 开发机执行）

在项目根目录执行以下命令即可生成预编译部署包（包含后端 JAR、仿真器 JAR、前端 `dist/` 与全套部署脚本）：

```powershell
.\scripts\package-docker-prebuilt.ps1
```

生成产物路径：`outputs\airport-ai-docker-prebuilt.tar.gz`

---

## 2. 上传预编译包到服务器 `/tmp/`（Windows 本机执行）

```powershell
scp outputs\airport-ai-docker-prebuilt.tar.gz root@<服务器IP>:/tmp/
```

---

## 3. 在 CentOS 7 服务器执行一键更新

### 首次使用新脚本（需先从压缩包提取更新脚本）

```bash
tar -xzf /tmp/airport-ai-docker-prebuilt.tar.gz -C /tmp scripts/docker-update.sh scripts/docker-start-simulators.sh
sudo bash /tmp/scripts/docker-update.sh --admin-pass <你的admin密码>
```

### 日常免密全自动更新

若已在 `/opt/airport-ai/repo/.env` 中写入 `SIM_ADMIN_PASSWORD=<密码>`（例如 `echo 'SIM_ADMIN_PASSWORD=你的admin密码' >> /opt/airport-ai/repo/.env`），以后每次上传新预编译包后只需执行：

```bash
sudo bash /opt/airport-ai/repo/scripts/docker-update.sh
```

执行后将全自动完成：
**数据库/代码/镜像三重备份 → 保留 `.env` 清理并解压预编译包 → 免 Maven/npm 下载秒级构建重启前后端容器 → 健康检查 → 自动批量拉起全部 20 台仿真体并等待上线**。

---

## 4. 常用维护与回滚命令（备查）

```bash
# 查看历史备份时间戳
sudo bash /opt/airport-ai/repo/scripts/docker-update.sh --list-backups

# 一键回滚到指定时间戳版本（自动恢复代码、数据库与历史镜像）
sudo bash /opt/airport-ai/repo/scripts/docker-update.sh --rollback <备份时间戳>

# 仅手动批量拉起容器内所有仿真体
sudo bash /opt/airport-ai/repo/scripts/docker-start-simulators.sh
```
