# SRS_F008 V1.132 独立复测与验收裁决

结论：**SRS_F008 整项 P，DEF-S3-085 在 V1.132 关闭**。执行基线 V2.3。产品提交 `5b9511a6daeafd9f740dd51a090d83f21a32195d`，标签 `V1.132`；Gemini/Claude 交接 `87db70a692ec64c4e6581161b3a989f6544f9d47`。GPT 从 `origin/ai/claude-fix` 合入 `ai/gpt-test`，独立构建并在自有 PostgreSQL schema `tip_gpt_f006_v118_20261030`、后端 18129、模型夹具 18117、机器人仿真体 18132 实跑。模板为本轮虚构任务族专用；为进入降级分支仅在 GPT 隔离 schema 将新建模板置为 ENABLED，结束后停用，**不以该夹具置位证明启用接口或试运行成功**。

## V1.132 当前实测

| 覆盖 | 观察 | 原始证据 |
| --- | --- | --- |
| TC-025.S2 / DEF-S3-085，解析缺值且原目标要求地点 | 原目标含 `F2_SERVICE_POINT`，`sceneParams={}`，模型返回 `destination=null`，模板默认 `F2_TEST_GATE`。任务 41 转 `PENDING_MANUAL`，场景参数保持空，计划及设备指令均无；事件含 `BASELINE_INPUT_DEFAULTED/ERR_LOCATION_UNRESOLVED` 和 `TASK_PENDING_MANUAL`，未标记完成。**P** | `evidence/SRS_F008-V1.132-missing-destination.json` |
| 解析成功 | 同为显式场景参数空，模型解析 `F2_SERVICE_POINT`。任务 42 场景参数及真实 `TASK_ACCEPT`、`EXECUTE_CAPABILITY` 的 `targetLocation` 均为 `F2_SERVICE_POINT`，`BASELINE_INPUT_BOUND` 留痕，机器人完成。**P** | `evidence/SRS_F008-V1.132-parsed-goal-r2.json` |
| 显式值优先 | 解析值 `F2_SERVICE_POINT`，显式输入 `F2_ALT_POINT`，模板默认 `F2_TEST_GATE`。任务 43 的场景参数及真实承接/执行指令均使用 `F2_ALT_POINT`。虚构地点不在模拟路线内，后续转待人工；这里只裁决绑定优先级 **P**，不声称完整执行成功。 | `evidence/SRS_F008-V1.132-explicit-priority.json` |
| 无地点目标 | 原目标不要求地点、模型未给目的地，任务 44 使用模板默认 `F2_TEST_GATE`，真实承接/执行指令一致并完成。说明缺值拦截没有误伤此类目标。**P** | `evidence/SRS_F008-V1.132-no-location-goal.json` |
| TC-027.S1 / R07，运行中版本冻结 | 任务 46 在 `EXECUTING` 时编辑已启用模板，模板 V1.0→V1.1 且新版本为草稿；运行计划冻结时间及步骤快照未改，机器人按原计划完成。**P** | `evidence/SRS_F008-V1.132-freeze-version.json` |
| R08 操作记录 | 任务 46 对应模板的创建、修改、停用在当前版操作记录中各有 `SUCCESS`。本夹具未调用启用接口；启用审计采用 V1.5 原始 API/数据库证据，经下述影响复核继续引用。**P** | `evidence/SRS_F008-V1.132-template-audit.json`；`evidence/TC-028-baseline-dryrun-audit.json` |

V1.129 的错误目的地真实执行记录和 V1.131 的解析缺值错误执行记录继续保留。V1.132 只代表本版观察，不改写旧版 F。`NT-S3-018` 所需目标映射观察已补齐，原 NT 保留并指向此结果。

## 历史覆盖影响复核

- 原始 V1.5 产品 SHA `0d798ceb53bc37498f353b4796f2081b92e2011b` 的 `TC-025.S1` 创建/顺序编辑/边界、`TC-027.S1` 启停与审计，以及 R01/R02/R04/R08 历史 P 保留原测试版本。V1.129 产品 SHA `bff5f210b69e418dbcaaaea70af0ff09897ab1e6` 的 42 组模板 API、页面错误提示、运动安全字段矩阵继续覆盖 `TC-026.S1/S2`、R03/R05/R06。V1.132 相比 V1.129 的 F008 相关变动集中在 `TemplateInputBinder`、`TaskPlanningOrchestrator`、`ReplanningService` 及其单测；`BaselineTemplateService`、`MotionSafetyGuard` 和基线模板编辑页未改。故静态校验、顺序/五步约束、编辑控件和安全字段的历史观察没有被当前改动直接影响。当前版又通过一条真实基线计划、版本冻结、操作日志与设备指令核心冒烟；**这些历史 P 不记作 V1.132 新执行次数**。
- F007 邻接受影响路径：当前版 CAP_NAVIGATION 真实指令保留正常 `targetLocation` 且成功；V1.126 产品 SHA `8405f0a44211ddc4fad842ea5b2d4a3f29e00ea9` 的运动安全拦截历史证据继续引用。当前修复没有修改 `MotionSafetyGuard` 或统一设备消息构造。局部重规划降级的保护分支另以本版定向单测覆盖，不把单测说成独立端到端观察。
- 本轮没有重新操作浏览器上移/下移或完整启用试运行 API。其 P 来源及版本如上；完整 95 项验收和 F009 及后续需求不在本裁决范围。

定向后端测试：`mvn -o test "-Dtest=TemplateInputBinderTest,BaselineDowngradeBindingF008Test,ReplanningHighRiskDowngradeTest,BaselineTemplateF008Test,BaselineTemplateSafetyTest,SceneParamsValidatorTest,ManualActionMissingInfoTest"`，**36 项，0 失败、0 错误、0 跳过，BUILD SUCCESS**。无产品代码修改、无需求基线调整。仅更新 F008 证据、台账及交接。所有测试地点、模板、任务、设备均为隔离环境虚构数据。
