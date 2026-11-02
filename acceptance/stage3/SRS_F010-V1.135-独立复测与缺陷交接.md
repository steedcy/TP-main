# SRS_F010 / V1.135 独立复测与缺陷交接

结论：**SRS_F010 未通过，交回修复方**。执行基线 V2.3；产品注解标签 `V1.135` 解引用为 `d18a5d9b0b95c38c91aa051e3297c90610bd8c94`，修复方交接提交 `6db2210d7b446b01072e329235bff6cb0586e989`。GPT 在 `ai/gpt-test` 接收该提交后独立构建；运行环境为专属 schema `tip_gpt_f006_v118_20261030`、后端 18129、受控目标理解模型 18117、既有 GPT 仿真体 18132。旧 F/NT 和旧版 P 证据均保留；本轮不把局部检查写为整步/整项 P。

## DEF-S3-032 仍为 F：嵌套身份字段漏检

原始证据：[`SRS_F010-V1.135-nested-identity-20261102.json`](evidence/SRS_F010-V1.135-nested-identity-20261102.json)。顶层 `passengerName`、`identityDocumentNumber` 和规范化写法 `PASSENGER-NAME` 均返回 HTTP 400、不建任务，见[`validation`](evidence/SRS_F010-V1.135-validation-20261102.json)。但将同一纯虚构哨兵放入 `sceneParams.metadata.passengerName` 后，提交成功并创建任务 67；任务详情原样保存 `FICTIONAL_NESTED_CANARY_135`，模型请求日志也包含该值。任务提交前后数量 51→52。任务 67 取证后由 GPT 取消为 `MANUAL_TERMINATED`。这违反 `TC-031.S2` 和 `SRS_F010.R06` 的“不保存旅客真实身份信息”，也影响关联的 `SRS_F024.R09`、`SRS_NF003.R01`；本轮未对后两项作整项裁决。代码核对显示 `SceneParamsPrivacyGuard.reject` 只遍历 `sceneParams.keySet()` 顶层键，未递归检查嵌套 Map/List，也未限制非必要的附加字段。

修复建议：在任务提交和补充等入口递归拒绝身份类字段，并按任务族声明约束可接收的场景字段；确认任务持久化和送模请求均不含虚构哨兵。旧任务中的历史哨兵仅为脱敏测试数据，原始失败证据保留。

## 已执行的局部观察

| 范围 | V1.135 观察 | 原始证据 |
| --- | --- | --- |
| `TC-031.S1` 边界与 `DEF-S3-029` 部分 | 空目标与 501 字返回 400；扩展定义缺必填 `targetLocation` 返回 400；请求前后任务数 46→46。1 字目标创建任务 63，目标理解完整并生成 1 个计划版本，随后因本机资源监督条件转人工。500 字、动态页面及类型边界尚未测。 | [`validation`](evidence/SRS_F010-V1.135-validation-20261102.json)、[`one character`](evidence/SRS_F010-V1.135-one-char-followup-20261102.json) |
| `TC-031.S3`、`TC-032.S1/S2` 部分 | 任务 64 补充后仍缺地点，计划 0，取消后 `MANUAL_TERMINATED`；任务 65 回答地点后进入上下文与计划，因本机监督条件转人工；任务 66 连续三轮未补齐，状态 `PLANNING→PLANNING→PLANNING→PENDING_MANUAL`，计划始终 0。第四轮被拒；对 66 发转基线/重试均 HTTP 400，计划与分配仍为 0。 | [`flow`](evidence/SRS_F010-V1.135-flow-20261102.json)、[`manual guard`](evidence/SRS_F010-V1.135-manual-guard-20261102.json) |
| `TC-031.S2` 隐私 | 顶层拦截通过；嵌套字段持久化并送模，**F**。 | [`validation`](evidence/SRS_F010-V1.135-validation-20261102.json)、[`nested identity`](evidence/SRS_F010-V1.135-nested-identity-20261102.json) |

模型夹具首次探针未读取 chunked 请求体，导致一次非产品性 HTTP 503；GPT 已修复夹具，任务 62 后续进入 `PENDING_MANUAL`，未据此判产品 F。上述局部观察只更新 `TC-031.S2`、`R06` 和 `DEF-S3-032` 的失败证据索引，其余步骤/规则保持原状态，待下一版按变更影响补测。

## 修复后仍需独立复测

1. `TC-031.S1` / R01 / `DEF-S3-028/029`：500 字边界、自动任务族、扩展定义前端动态字段及必填/整数/浮点/布尔类型边界。
2. `TC-031.S2` / R02/R06：六项提取、特殊旅客仅保存协助类型、顶层和嵌套身份字段、模型请求和持久化。
3. `TC-031.S3` / R05/R08、`TC-032.S1/S2` / R03/R04/R09/R10：原文与事件、补齐后规划、三轮上限及 `DEF-S3-063` 无计划无设备命令。
4. `TC-033.S1`：范围外目标、无在线代理；`TC-034.S1/S2` / R07 / `DEF-S3-033`：60 秒超时、模型异常、有/无可用基线分支、只允许经校验的降级执行及故障期间读取；邻接态势/任务列表与基线降级冒烟。

本轮不修改产品代码、F009 台账、其他 worktree、未跟踪 `document/` 或 F020–F022 WIP。自有模型夹具和后端在交接时停止，GPT 仿真体保持原配置。
