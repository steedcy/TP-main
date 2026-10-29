# SRS_F003 V1.113 独立复测与缺陷交接

- 版本：`V1.113`，代码 `b5f32f8985c61c2a757864906b87556f7deb6bb6`；接收 Claude 交接提交 `a4f55988b6eecd121f410efebcb3af1c39da172635a15b746`，GPT 合并提交以 Git 日志为准。
- 环境：Windows 本机 GPT 独立工作目录；隔离 PostgreSQL schema `tip_gpt_f002_v111_20261029`；后端 `127.0.0.1:18105`；Edge 无头浏览器经独立 Vite `127.0.0.1:15174`；本地仿真器 `18110`。未使用 Claude schema/端口；未接触共享 PostgreSQL 数据。
- 构建：`mvn -o -DskipTests package` 成功，`npm run build` 成功。构建不作为验收通过证据。
- 本轮结果：TC-008～TC-010 共9步：P=3（TC-008.S3、TC-009.S2、TC-010.S1），F=1（TC-010.S2），NT=5；R01～R08：P=4（R01、R02、R03、R05），F=2（R04、R06），NT=2（R07、R08）。**SRS_F003 未通过，不能推进 F004。**旧版 P/F/NT 证据保留，新版未实测部分不继承旧 P。

## 已验证的结果

- TC-008.S1 子检查：Edge 表单默认仿真体、类型与其他空项、周期15秒；API 对非法编码、超长编码、空/超长名称、非五类、缺模拟类型、非预置区域、4/61秒、201字备注均拒绝；冲突编码提示包含实际编码。仍缺完整边界与编辑验证，整步 NT。证据 `acceptance/stage3/evidence/SRS_F003-V1.113-phase1.json`、`acceptance/stage3/evidence/SRS_F003-V1.113-ui.json`。
- TC-008.S2 子检查：Edge 有必需列、在线筛选入口与编码检索；API 可按离线筛选。类型/在线组合及分页交互未全部执行，整步 NT。
- TC-008.S3 / R05：活动对象9→20，第21个合法对象409并提示上限20，数量不变。清理诊断见下方，额外复核后这些临时对象均已删除。证据 `acceptance/stage3/evidence/SRS_F003-V1.113-limit.json`、`acceptance/stage3/evidence/SRS_F003-V1.113-diagnostic-correction.json`。
- TC-009.S1/S2/S3 子检查：真仿真器握手 PASSED 且返回耗时，随后可创建代理；不可达、非法JSON、读超时均保存不同失败原因并拒绝创建启用代理；接入地址变更重置 UNTESTED；API 凭据无原值，停用后未重测无法启用、重测后可启用。Edge 耗时和编辑掩码待测。证据 `acceptance/stage3/evidence/SRS_F003-V1.113-connection.json`。
- TC-010.S1：对同一代理关联的待分配、降级执行中、执行中正式任务逐一删除均 409，任务状态及设备活动状态未变。证据 `acceptance/stage3/evidence/SRS_F003-V1.113-r06.json`。
- V17：在 GPT 隔离库单个无代理仿真体上移除 `CAP_SIM_STATUS` 后，将 V17 原 SQL 执行两次：第一次补1条，第二次补0条；恢复为 UNTESTED。证据 `acceptance/stage3/evidence/SRS_F003-V1.113-v17.json`。

## 待 Claude 修复/核对

1. **DEF-S3-077 / TC-010.S2 / R06（明确失败）**：代理有待分配任务步骤关联，但 `current_task_id=NULL`。停用返回200，代理变停用离线；步骤仍 `PENDING_ASSIGNMENT`，`AGENT_OCCUPATION_RELEASED` 事件计数0→0。`releaseAgentOccupation()` 只检查 `current_task_id`，而删除路径已会查询 `task_step_assignments`。请覆盖待分配关联的恢复与释放，并用相同 fixture 定向回归。证据 `acceptance/stage3/evidence/SRS_F003-V1.113-r06.json`。
2. **DEF-S3-076 / R04（能力画像偏差，需核对规格实现口径）**：四类新建仿真体实例的 `/capabilities` 均只有 `CAP_SIM_STATUS`，没有对应模拟类型的业务能力实例。需求5.2.1 R04 要求“据此加载能力画像”，5.2.4A 还要求仿真体继承模拟类型能力。请修复自动/可重复加载机制，或明确现有实例能力建立流程并给出可实测的完整画像路径；不得靠改变 P/F 标准处理。证据 `acceptance/stage3/evidence/SRS_F003-V1.113-phase1.json`。
3. 预置区域清单：需求未给具体值，本轮只用演示 `F2_TEST` 检验下拉与服务端拒绝非预置区域。若需正式区域清单，先在 `docs/BASELINE_CHANGES.md` 登记基线/配置决策；不阻塞上述产品缺陷修复。

## 原始诊断与未执行范围

- 读超时原脚本把连续两个共用 URL 的失败探针误判为“应重置未测试”；未改 URL 时保留 FAILED 正确。原始 `pass=false` 保留在 `acceptance/stage3/evidence/SRS_F003-V1.113-connection.json`；更正依据与实际失败原因在 `acceptance/stage3/evidence/SRS_F003-V1.113-diagnostic-correction.json`。该误判不构成产品 F。
- 上限夹具首次清理时记录 HTTP200 但立即读数仍为20；后续按同一编码逐条 DELETE 后活动 G3L 对象归零。原始结果保留，TC-010.S3 的确认/删除/审计仍 NT，不把此诊断算作通过。
- TC-008.S1/S2 的剩余边界与筛选分页、TC-009.S1/S3 的浏览器耗时与凭据编辑、TC-010.S3 的确认/归档/审计，以及 R07/R08 全范围，待下一版本完整补证。TC-017.S3/TC-093.S1 的能力画像邻接回归也待做。

基线文档与95项用例本轮未修改；公司版用例未使用。
