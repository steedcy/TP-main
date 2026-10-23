# 智慧机场人工智能集群协同服务平台

对齐基线：`20260904-智慧机场人工智能集群协同服务平台-需求规格说明书-V1.4.md` + 附录A/B/C/D/E（V2.0）+ 数据库设计说明书（V2.0）。

## 项目结构

```
backend/    Spring Boot单体应用（对应附录A技术架构规范V2.0）
simulator/  独立设备仿真运行时（P2/P3四类设备驱动）
frontend/   Vue 3 + Ant Design Vue管理后台
scripts/    本地开发环境启动脚本
```

## 后端

- Java 17 + Spring Boot 3.2.5 + PostgreSQL 15 + Redis 7.2
- 数据库迁移脚本：`backend/src/main/resources/db/migration/`（Flyway，V1建表，V2任务规划相关表，V3初始化数据）
- 已实现骨架：
  - 用户认证（登录/密码锁定/解锁，对应5.1.1）
  - 会话管理（Redis，30分钟空闲失效，对应SRS_NF002）
  - 设备接入与代理（连接测试、心跳超时判定，对应5.2.1~5.2.3）
  - 监督判定核心逻辑（三类确定性规则+风险信号组合，对应5.4.5、TBD-03/TBD-04）
  - 基线模板匹配（对应5.4.6降级优先级）
  - 规划模型服务调用抽象（对应附录A 3.4节，可替换实现）
  - 任务事件仅追加约束（对应5.7.1）

本地启动：
```bash
./scripts/start-backend.ps1
```

需要预先启动PostgreSQL（`airport_ai`库）和Redis，或通过环境变量`DB_HOST`/`DB_PORT`/`DB_USERNAME`/`DB_PASSWORD`/`REDIS_HOST`/`REDIS_PORT`指向已有实例。

首次部署在Flyway应用V3后，管理员账号为不可登录的占位密码。开放服务前按《部署实施手册》运行`python3 scripts/bootstrap-admin.py`设置真实密码；该工具以静默交互读取密码，只更新占位账号，要求Python 3、JDK/Maven和`psql`。

设备代理通信使用每台设备独立的Bearer令牌。启动前请设置`DEVICE_CREDENTIAL_ENCRYPTION_KEY`（建议至少32个随机字符）；在设备管理中轮换令牌后，明文仅显示一次，需配置到对应设备或后续仿真体实例。令牌摘要与加密副本由平台保存，用于校验设备上报和发起代理命令。连接测试会访问设备档案的`accessEndpoint`下`/device-api/v1/health`，创建代理后平台会发送绑定请求。

### 设备仿真运行时（P2/P3）

`simulator/`是独立Spring Boot进程，使用`SIMULATOR`设备档案和`SIMULATED_DEVICE_TYPE`选择`SMART_DISPLAY`、`BAGGAGE_SCANNER`、`FLIGHT_DELAY_BOARD`或`MOBILE_ROBOT`驱动。它使用设备独立Bearer令牌响应平台健康握手、绑定代理、周期上报状态并接收任务命令。通过设备管理的“轮换令牌”获取令牌后，将同一令牌配置给仿真进程；令牌不会写入仓库。

在仿真设备档案中将接入地址设为`http://localhost:8091`，配置类型`SIMULATOR`、模拟类型`SMART_DISPLAY`，启动前设置：

```powershell
$env:SIMULATOR_DEVICE_CODE='SIM_DISPLAY_001'
$env:SIMULATOR_DEVICE_TOKEN='<设备令牌>'
$env:SIMULATED_DEVICE_TYPE='SMART_DISPLAY'
$env:SIMULATOR_EXECUTION_DELAY_MS='500'
$env:SIMULATOR_SCENARIO_RESULT='SUCCESS'
./scripts/start-simulator.ps1
```

启动脚本从项目根目录运行；也可直接使用Maven启动。`start-backend.ps1`检查设备凭据加密密钥，`start-simulator.ps1`检查设备编号、设备令牌和`SIMULATED_DEVICE_TYPE`。脚本不会打印或保存令牌。后端需先配置可用的PostgreSQL、Redis和加密密钥；仿真器需配置设备档案对应的设备令牌。

成功场景之外可将`SIMULATOR_SCENARIO_RESULT`设为`FAILED`或`TIMEOUT`重复演示设备错误和超时；`NO_OBJECT`用于行李测量无对象，`LOST_TARGET`用于机器人陪同目标丢失。`SIMULATOR_HEARTBEAT_INTERVAL_SECONDS`默认15秒，位置和所属区域可用`SIMULATOR_X`、`SIMULATOR_Y`、`SIMULATOR_ZONE`设置。行李默认尺寸/重量可用`SIMULATOR_BAGGAGE_LENGTH_CM`、`SIMULATOR_BAGGAGE_WIDTH_CM`、`SIMULATOR_BAGGAGE_HEIGHT_CM`、`SIMULATOR_BAGGAGE_WEIGHT_KG`设置。`SIMULATOR_AGENT_CODE`与`SIMULATOR_REPORT_URL`可选；配置后进程重启会恢复绑定并继续上报。`POST /device-api/v1/control/online?value=false`（需相同Bearer令牌）用于暂停心跳演示离线，设为`true`后恢复上报。此控制端点属于本地仿真器，不应暴露到不可信网络。

运行时协议与设备输入输出字段见《智慧航显仿真运行时-P2验收记录》。

## 前端

- Vue 3 + Vite + Ant Design Vue + Pinia + Vue Router
- 已实现骨架：登录页、账号管理、设备管理、能力边界配置、基线模板、风险规则配置、运行总览、任务列表/详情、仿真控制台、二维态势展示（5秒快照轮询）、操作记录

配置管理员可在“仿真控制”中启动/停止仿真体逻辑运行状态、设置仿真结果场景、创建三类演示任务并查询最近设备事件和命令。停止后实例报告离线、暂停心跳并拒绝新的承接/执行命令；运行进程继续在线，以便管理端恢复，进程启动/重启仍由部署环境负责。二维态势快照采用`GET /api/v1/situation/snapshot`每5秒轮询；服务端WebSocket暂未实现。

本地启动：
```bash
cd frontend
npm install
npm run dev
```

默认通过Vite代理将`/api`转发到`http://localhost:8080`。

## 尚未接入/待确认

本轮开发分阶段验收矩阵见[`document/P5需求差距收口与验收矩阵.md`](document/P5需求差距收口与验收矩阵.md)，P5阶段结论见[`document/P5阶段验收与评估结论.md`](document/P5阶段验收与评估结论.md)。本机PostgreSQL端口可达，但项目默认账号认证失败，应用未能启动且Flyway迁移未执行；Redis无认证PING正常，但平台会话集成未验证。仍需有效数据库配置和规划/监督服务配置完成最终部署/业务验收。性能压测、8小时稳定性、浏览器现场验收和真实外部模型调用也未执行。候选设备排序权重仍需确认并按确认规则验收；WebSocket当前由5秒HTTP快照轮询替代。
