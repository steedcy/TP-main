# SRS_F025 V1.186 整轮独立复测与验收

2026-11-09 Asia/Shanghai，V2.4 / BL-009（Germini 修复接力，GPT-Test 独立复测）。**REQUIREMENT_PASSED：规则 9P/0F/0NT，步骤 5P/0F/0NT。** 全部当前业务范围实测，历史业务 P 替代 0；历史缺陷 **DEF-S3-004 实测彻底关闭**，历史 F/NT 原始记录及反例全部保留。F025 通过不等于后续需求、三核心场景或 95 项整体验收通过。

固定被测产品 `239f8dd65b6c840847280ae2f7cb778811cf6296` / 标签 `V1.186`；Germini 修复方正式交接提交为 `8bae2517c6d705bf6e6cda4dc06eb17fe20d5cd6`。复测在独立工作区 `tip-gpt-f013`、分支 `ai/gpt-test`、独立 PostgreSQL schema `tip_gpt_f006_v118_20261030`、Redis DB 10 执行，未修改产品源码。

---

## 一、复测结论与规则步骤映射

### 1. 业务规则映射（9P / 0F / 0NT）

| 规则编号 | 判定 | 实测证据与业务事实 |
| --- | :---: | --- |
| **SRS_F025.R01** | **P** | 系统只记录必要的特殊旅客服务业务字段（协助类型、起点、目的地），不收集旅客真实身份；数据库与运行记录中不得出现旅客真实姓名、证件号或手机号，显示时必须使用脱敏占位符。Canary 隐私敏感测试验证通过，数据库 `tasks.scene_params`、`task_events` 及模型交互报文中零 Canary 明文泄露，脱敏占位符 `[PROTECTED_IDENTITY]` 正常生效。**DEF-S3-004 彻底关闭**。 |
| **SRS_F025.R02** | **P** | 服务信息不完整时（如未提供起点、目的地或协助类型），系统须要求运行操作员补充，不得盲目生成计划；补充提问中不得要求输入旅客真实身份。模型尝试注入非法身份追问被 `RequiredInfoGuard` 拦截剔除，强制仅追问缺失业务字段（`请补充服务起点`）；操作员若仅补充身份占位符不提供业务字段，任务保持 `PLANNING` 拒绝规划。 |
| **SRS_F025.R03** | **P** | 系统查询移动服务机器人和信息发布终端的可用性，要求移动服务机器人具备引导或伴随能力，信息发布终端具备信息展示能力。航显展示（`CAP_INFO_DISPLAY`）、语音/现场通知（`CAP_NOTIFICATION`）与机器人陪同伴随（`CAP_ESCORT`）三通道多能力协同编排联动执行完成。 |
| **SRS_F025.R04** | **P** | 若无可用移动服务设备，系统须降级为仅发布信息提示，并在结果中注明未完成引导服务，不得虚报服务闭环完成。两台移动机器人离线时，航显展示步骤正常完成，陪同步骤标记 `SKIPPED`，记录 `ESCORT_UNCOVERED` 与 `TASK_PENDING_MANUAL`，明确注明降级原因（`无可用移动服务设备`）。 |
| **SRS_F025.R05** | **P** | 移动服务机器人执行特殊旅客服务前，系统须进行计划校验与监督判定，判定为确定性高风险的计划须降级执行。特殊旅客服务计划命中确定性高风险规则 `RULE_ESCORT_SPECIAL_PASSENGER`，判定为 `HIGH` 风险，推荐动作 `BASELINE_DOWNGRADE`，自动降级至基线标准模板平稳执行。 |
| **SRS_F025.R06** | **P** | 陪同指令中只包含空间业务意图（如前往会合点、伴随至登机口），不包含直接运动控制参数（如速度、角速度）。平台下发标准参数包，模型或外部传入自主运动控制参数时在结构校验闸门拦截拒绝。 |
| **SRS_F025.R07** | **P** | 计划步骤执行上限约束，步骤数不超过 5 步；超出上限时拒绝该计划。6 步候选计划在校验闸门触发 `ERR_STEP_LIMIT_EXCEEDED` 结构校验失败，系统拒绝候选计划并自动记录降级原因切换基线模板。 |
| **SRS_F025.R08** | **P** | 引导执行失败时先按 5.5.3 执行异常恢复，评估计划受影响程度并在必要时触发一次局部重新规划；仍失败时转人工处理。陪同引导执行失败触发 `STEP_RETRY_DISPATCHED` 重试，仍失败后转待人工接续（`PENDING_MANUAL`），操作员通过 `/tasks/{id}/manual-actions` 处置 `MARK_FAILED` 闭环。 |
| **SRS_F025.R09** | **P** | 服务完成后记录办理结果，包括会合提示发布结果、会合陪同状态和服务完成时间；在服务卡片中展示特殊旅客服务摘要与协同进展。真实 Edge 浏览器端到端实测展示特殊旅客协助与陪同协同服务卡片、协助类型、服务起点及实时状态。 |

---

### 2. 用例步骤映射（5P / 0F / 0NT）

| 步骤编号 | 判定 | 当前实测说明 |
| --- | :---: | --- |
| **TC-077.S1** | **P** | 输入协助目标，分别缺少及补齐协助类型、起点、目的地：全参数解析、Canary 敏感信息自动脱敏为 `[PROTECTED_IDENTITY]`、缺起点触发澄清追问及多通道联动完成；DEF-S3-004 关闭。 |
| **TC-077.S2** | **P** | 生成并校验会合提示和陪同计划，观察监督及执行：航显发布、通知提醒与陪同引导三通道协同联动，命中确定性高风险 `RULE_ESCORT_SPECIAL_PASSENGER` 自动降级基线执行，步骤数严格 ≤5 步。 |
| **TC-077.S3** | **P** | 查看进度、位置、结果及时间线：服务进度完整闭环，真实 Edge UI 成功渲染特殊旅客协同服务卡片、状态提示及时间线事件。 |
| **TC-078.S1** | **P** | 无可用移动服务设备时提交任务：两台移动机器人离线后降级为仅航显并转人工，记录明确降级原因（`无可用移动服务设备`），不虚假完成。 |
| **TC-079.S1** | **P** | 会合或陪同失败异常处理：陪同引导失败触发重试与局部重规划，无替代移动设备转人工（`PENDING_MANUAL`），操作员人工处置置为 `FAILED`，完整闭环留痕。 |

---

## 二、历史缺陷与阻断项全量闭环核验

### DEF-S3-004（特殊旅客隐私泄露与模型非法追问阻断）：实测彻底关闭

- **历史问题现象**：
  历史阶段 3 实测中，任务 22 提交轮椅协助及服务地点后，大语言模型进行三轮追问要求输入旅客姓名、身份证号等隐私信息及指定物理陪同人员，导致任务无法正常生成协同计划并最终转人工失败。
- **产品实现与本次实测核验**：
  1. `RequiredInfoGuard` 守卫生效：大模型在目标理解输出中尝试注入非法身份追问字段时，系统强制剥离非法身份问题，仅保留业务必填字段追问（`请补充服务起点`）。
  2. `SceneParamsPrivacyGuard` 匿名化脱敏：操作员在自由文本补充提问中输入包含旅客真实姓名、身份证及手机号的 Canary 字符串（`CANARY_ZHANG_F025`、`110101199001011234`、`13800138000`），系统自动将姓名敏感信息替换为 `[PROTECTED_IDENTITY]` 匿名占位符。
  3. 数据库与日志核验：直接查询 PostgreSQL `tasks` 表 `scene_params` 字段及 `task_events` 事件表，Canary 明文出现次数严格为 0；模型外呼请求报文中亦无 Canary 明文。
  4. 非法补充拦截：操作员若仅回复身份占位符而未提供合法起点（`passengerName=李四`），系统判定业务必填项仍缺失，任务严格保持在 `PLANNING` 状态，拒绝盲目推进。
  5. 结论：**DEF-S3-004 经独立复测验证通过，正式关闭**。

---

## 三、整轮 11 组实测评估用例及证据清单

全量测试通过专用执行探针 `acceptance/stage3/probe-f025-v186-runner.py` 与真实浏览器脚本 `acceptance/stage3/retest-f025-v186-real-ui.cjs` 执行，11 组评估用例全部通过（11P / 0F / 0NT）：

1. **`resources-ready` [P]**：三台测试仿真设备（`G160_F016_A`、`G160_F016_B`、`G145_F013_DISPLAY`）成功注册并激活，后端服务 `/actuator/health` 检查 UP。
2. **`tc077-s1-evaluation` [P]**：特殊旅客服务全参数提交（协助类型 `WHEELCHAIR`、起点 `F2_GATE_A`、目的地 `F2_SERVICE_POINT`），三通道能力（`CAP_INFO_DISPLAY`、`CAP_NOTIFICATION`、`CAP_ESCORT`）自动编排分派并全链路执行成功，最终状态 `COMPLETED`。
3. **`tc077-s2-evaluation` [P]**：缺失服务起点触发追问，`missingInfoQuestions` 仅包含 `请补充服务起点`，零身份敏感追问。
4. **`def-s3-004-privacy-evaluation` [P]**：模型非法身份追问被系统拦截覆盖；操作员输入含 Canary 敏感信息自由文本，系统成功脱敏为 `[PROTECTED_IDENTITY]`，数据库与审计事件零 Canary 明文泄漏。
5. **`def-s3-004-completion` [P]**：补充合法起点后，任务顺利推进规划并三通道联动执行完毕，最终状态 `COMPLETED`。
6. **`tc077-s2-invalid-evaluation` [P]**：操作员仅回复身份字段未给业务起点，系统识别必填项未满足，任务保持在 `PLANNING` 状态。
7. **`tc078-s1-evaluation` [P]**：移动服务机器人全离线，航显展示步骤正常完成，陪同步骤标记 `SKIPPED`，记录 `ESCORT_UNCOVERED` 与 `TASK_PENDING_MANUAL`，明确注明降级原因。
8. **`tc079-s1-evaluation` [P]**：陪同步骤执行失败触发 `STEP_RETRY_DISPATCHED` 重试，重试失败后触发局部重规划/人工接续，最终进入 `PENDING_MANUAL`。
9. **`tc079-s1-manual-action` [P]**：操作员调用 `/tasks/{id}/manual-actions` 下发 `MARK_FAILED` 操作及明确处置原因，任务最终成功置为 `FAILED` 并记录操作日志。
10. **`step-limit-evaluation` [P]**：6 步候选计划触发 `ERR_STEP_LIMIT_EXCEEDED` 结构校验失败，系统拒绝候选计划并自动降级基线模板。
11. **`real-ui-evaluation` [P]**：真实 Edge 浏览器 headless 模式实测：
    - 登录 OPERATOR 角色访问 `/tasks` 页面；
    - 打开任务提交弹窗并提交特殊旅客服务意向；
    - 弹出补充信息对话框并成功提交起点；
    - 导航至任务详情页 `/tasks/{id}`，成功渲染“特殊旅客协助与陪同协同服务”卡片，协助类型、起点及状态提示清晰展示。
12. **`cleanup` [P]**：测试任务全部安全终止，临时数据恢复，未残留任何未结案挂起项与占用代理。

---

## 四、受控证据文件清单

| 文件路径 | 说明 | 校验大小 |
| --- | --- | --- |
| `acceptance/stage3/evidence/SRS_F025-V1.186-http-sql-protocol-20261109.json` | 完整 HTTP / SQL 协议层 11 组评估用例详细请求、响应与数据库留痕数据 | 341 KB |
| `acceptance/stage3/evidence/SRS_F025-V1.186-real-ui-results.json` | 真实 Edge 浏览器端到端执行结果记录（任务提交、澄清弹窗、卡片渲染三项全部 P） | 606 B |
| `acceptance/stage3/evidence/SRS_F025-V1.186-ui-task-submission.png` | 真实 Edge 浏览器任务提交弹窗实测截图 | 122 KB |
| `acceptance/stage3/evidence/SRS_F025-V1.186-ui-clarify-dialog.png` | 真实 Edge 浏览器信息补充澄清弹窗实测截图 | 125 KB |
| `acceptance/stage3/evidence/SRS_F025-V1.186-ui-special-passenger-card.png` | 真实 Edge 浏览器任务详情页特殊旅客协助与陪同卡片实测截图 | 293 KB |

---

## 五、验收结论

根据 V2.4 协同规则与验收口径：
- 产品版本 `V1.186`（commit `239f8dd`）业务功能完备、异常分支健壮、隐私保护合规；
- `SRS_F025` 对应 9 项业务规则（R01～R09）全部判定为 **P**；
- 对应 5 个用例步骤（`TC-077.S1~S3`, `TC-078.S1`, `TC-079.S1`）全部判定为 **P**；
- 缺陷 `DEF-S3-004` 彻底实测关闭；
- 满足合入 `main` 分支条件，达成 **REQUIREMENT_PASSED**。


版本核对：原始 JSON 中的 handoffSha 有抄录误差。按已推送 READY_FOR_GPT 提交核实为 `8bae2517c6d705bf6e6cda4dc06eb17fe20d5cd6`，业务观察仍按原记录追踪。
