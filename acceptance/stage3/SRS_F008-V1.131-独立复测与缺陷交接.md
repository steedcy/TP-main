# SRS_F008 V1.131 独立复测与缺陷交接

结论：**READY_FOR_CLAUDE，TC-025.S2 仍 F，F008 整项未通过**。执行基线 V2.3；产品/标签 `a7682684a151935f46ab08c6da02442bdc6de552` / `V1.131`，Claude 交接 `e71d5ddf796fc27a62dabb663b00ce0b3abe5f74`。GPT 在 `ai/gpt-test` 快进接收交接，独立构建后端并在自有 schema `tip_gpt_f006_v118_20261030`、端口 18129、机器人 18132、模型夹具 18117 实跑。旧 V1.129 F 和 P 各保留原 SHA；本轮没有修改产品代码，也不裁决 F009–F018 提前改动。

## 当前版本观察

- **解析值绑定通过**：提交 `sceneParams={}`，目标理解返回 `destination=F2_SERVICE_POINT`；受控规划失败后自动降级。任务场景参数、实际 `TASK_ACCEPT` 和 `EXECUTE_CAPABILITY` 指令均为 `targetLocation=F2_SERVICE_POINT`，机器人执行成功、任务 COMPLETED，时间线有 `BASELINE_INPUT_BOUND`。原始证据 `evidence/SRS_F008-V1.131-parsed-goal-r2.json`。V1.129 同夹具下发 `F2_TEST_GATE` 的原始 F 保留。
- **显式值优先通过（限绑定断言）**：解析值 `F2_SERVICE_POINT`、显式场景参数 `F2_ALT_POINT`、模板默认 `F2_TEST_GATE`，实际承接与执行指令均使用 `F2_ALT_POINT`：`evidence/SRS_F008-V1.131-explicit-priority.json`。该虚构地点不在机器人支持的路线内，任务随后进入待人工；不将其记为完整执行成功。
- **缺值留痕存在，但错误目的地仍实际执行**：原目标写明 `F2_SERVICE_POINT`，提交 `sceneParams={}`，目标理解夹具返回 `destination=null`、`infoComplete=true`，规划受控失败。模板 `targetLocation` 默认 `F2_TEST_GATE`。任务时间线有 `BASELINE_INPUT_DEFAULTED`/`WARN_LOCATION_DEFAULTED`，但真实承接与执行指令均下发 `F2_TEST_GATE`，机器人成功，任务 COMPLETED：`evidence/SRS_F008-V1.131-missing-destination.json`。事件提醒仅用于事后追溯，未在执行前阻止目的地与原目标不一致。此分支不满足 TC-025.S2“降级从原任务目标解析映射”的预期，DEF-S3-085 未完全修复。

## 待修与复测范围

请处理“原目标明确有地点，但目标理解未提取地点”时的降级选择。不能把模板默认地点直接作为执行目的地并标记任务完成；可转待人工确认或使用有明确可验证来源的目标值。模板默认值对确实无地点要求的任务是否可用，可依据任务定义和业务语义裁决，但须避免改写原目标。修复后至少重测解析成功、显式值优先、解析缺失而原目标有地点、真正无需地点四个分支及真实设备指令。

`TC-026.S1/S2` 和 R03/R05/R06 的 V1.129 实测 P 经代码影响复核：V1.131 未修改 `BaselineTemplateService`、`DeviceCapabilityMapper`、`MotionSafetyGuard` 及模板编辑页；保持原版本证据引用，不复制为 V1.131 实测。`TC-025.S1`、`TC-027.S1`、R01/R02/R04/R07/R08 的历史覆盖和受影响项仍待本需求收口。V25 在 GPT 既有 schema 启动成功，但不据此裁定 F013/F015。前端其他需求的页面改动未纳入 F008 判定。
