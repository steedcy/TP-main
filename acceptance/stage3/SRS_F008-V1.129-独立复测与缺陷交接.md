# SRS_F008 V1.129 独立复测与缺陷交接

结论：**READY_FOR_CLAUDE，整项未通过**（执行/用例基线 V2.3）。待测产品与标签 `bff5f210b69e418dbcaaaea70af0ff09897ab1e6` / `V1.129`；Claude 正式交接 `5b0336475797719f573f7de3a29f6096599ad634`。GPT 在 `ai/gpt-test` 独立接收该提交；本报告不裁决同版提前纳入的 F009–F012，也不表示全部 95 用例通过。

## 当前版本实测

- `TC-026.S1`、`SRS_F008.R03/R05`：GPT 专用 schema `tip_gpt_f006_v118_20261030`、后端 18129、`V1.129` 独立构建，真实 HTTP 42 组请求中，合法前序输出、类型兼容（含 Integer→Integer）和正常模板保存为草稿；不存在的输出、Boolean→String 类型冲突、当前/后序/零号步骤引用、非法来源、重复名称、六步、能力缺口、未定义输入与未映射必填输入被拒。创建的测试模板均删除，前后模板 ID 集合一致。原始响应和清理结果：`evidence/SRS_F008-V1.129-template-api.json`。
- `TC-026.S2`、`SRS_F008.R06`：同批真实 HTTP 中 21 种运动安全映射目标和 7 种完成条件均拒绝；业务指标 `waypointCount` 作为完成条件及前序输出可保存。前端 `npm run build` 成功。Edge 页面把不存在的前序输出提交给真实后端后返回 400，错误气泡完整显示“步骤2…没有输出参数”，编辑弹窗未关闭：`evidence/SRS_F008-V1.129-ui-error-r4.json`、同名 PNG。前两次按钮定位错误记录在 `...ui-error.json` 和 `...ui-error-r3.json`，属于探针诊断，不计产品 F。
- `TC-025.S2` 对照：GPT 自有移动机器人仿真体 18132、目标场景参数显式为 `F2_SERVICE_POINT` 时，模板默认 `F2_TEST_GATE` 被显式值覆盖，基线计划结构/能力/约束校验通过，机器人完成 CAP_NAVIGATION：`evidence/SRS_F008-V1.129-downgrade-mapping.json`。该对照通过隔离库把自建模板置为 ENABLED、把模型服务失败后自建任务置为 PENDING_MANUAL，以真实人工切换接口和设备链路验证映射；不将夹具置位当作启用或目标理解业务验收。

## 产品缺陷 DEF-S3-085：降级任务忽略目标理解解析出的目的地

`TC-025.S2` 原预期包含“降级从原任务目标解析映射”。GPT 在 18117 启动隔离目标理解夹具，返回 `destination=F2_SERVICE_POINT` 且信息完整；规划端返回受控失败以触发基线降级。提交任务时 `sceneParams={}`，原目标文本含 `F2_SERVICE_POINT`。隔离库中只将 GPT 自建模板置为 ENABLED 作为前置夹具，模板输入 `targetLocation` 的默认值特意设为不同的 `F2_TEST_GATE`。

真实 `POST /tasks` 成功，任务的 `goalParsingResult.destination` 为 `F2_SERVICE_POINT`；降级后 `sceneParams.targetLocation` 却成为 `F2_TEST_GATE`。真实 `TASK_ACCEPT` 和 `EXECUTE_CAPABILITY` 的 `inputParams.targetLocation` 均为 `F2_TEST_GATE`，设备回执成功，任务状态 `COMPLETED`。即把解析出的目标丢失并执行了模板默认地点。原始请求/响应、计划、任务、指令载荷和清理记录在 `evidence/SRS_F008-V1.129-parsed-goal-r2.json`。首次探针 `...parsed-goal.json` 的模型夹具未处理分块请求，返回 503；修正夹具后获得上述可复现产品偏差，首次记录保留为夹具诊断。

裁决：`TC-025.S2=F`、`DEF-S3-085` 待修。旧 `NT-S3-018` 的缺口已补测并转为该产品 F；旧 NT 不删除。修复需让解析出的目的地以明确优先级进入降级模板输入，显式场景参数不得被覆盖；缺少可用解析值时避免默认值悄悄改写目标。复测自然语言解析、显式覆盖、缺值和真实执行链路。

## 尚待本需求收口

`TC-025.S1`、`TC-027.S1` 及 R01/R02/R04/R07/R08 保留原测试版本 P，不复制成 V1.129 全项实测 P。当前版正常模板创建/顺序与重复名称已有定向冒烟，但页面上移/下移、启用模板修改时运行任务的冻结版本、启停与操作记录仍需按产品改动影响复核或补测。F007 统一消息与运动安全字段已有 V1.126 历史 P；V1.129 的 `MotionSafetyGuard.waypointCount` 放行对计划/任务调用方有影响，下一轮针对该邻接补测。F009 试运行结果审计和 F010–F012 提前改动均留各自阶段裁决。

`issues.csv` 中 F003 的 DEF-S3-011/012/013/014/038 此前仍写“待修复”，本轮按 V1.113 修复记录及 `SRS_F003-V1.115-独立复测与验收裁决.md` 有说明地更正状态，保留原证据及原事实，不重开产品缺陷。

本轮所有账号、任务、模板、地点与设备均为 GPT 隔离环境的虚构数据。未触碰 Claude 的 worktree、数据库和端口；未修改产品代码。前端 Vite 15179、后端 18129、机器人 18132、模型夹具 18117 均属 GPT；退出前会核对进程归属并停止本轮启动的进程。
