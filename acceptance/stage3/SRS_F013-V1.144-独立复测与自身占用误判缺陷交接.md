# SRS_F013 V1.144 独立复测与自身占用误判缺陷交接

- 日期：2026-11-03（Asia/Shanghai）；执行/用例基线V2.3。
- 标签 `V1.144` → `614f0407ce2345176e87bfcb15cf1b1cd3ca0313`，交接 `4ae6d1cb32a65a95c39d97f5874002f6c69ff704`，已fetch并快进合入独立 `tip-gpt-f013` / `ai/gpt-test`。
- **裁决：READY_FOR_CLAUDE。原DEF-S3-092真实复测通过；受影响的局部重规划邻接发现DEF-S3-093，R03仍F，F013整项未通过。** 按V2.3及时交修，未合main或推进F014。

## DEF-S3-092通过：外部占用硬拒绝，空闲候选保留软风险分支

从V1.144源码独立离线打包成功并启动真实JAR。任务145在GPT机器人NO_FEEDBACK场景下真实EXECUTING，占用唯一代理 `AGT-803437A3`，ONLINE/BUSY/currentTaskId=145；竞争任务146在资源风险规则已恢复启用的情况下提交，结构/能力PASS、约束FAIL，原因 `ERR_RESOURCE_CONFLICT`，未冻结、未监督、零分配/指令。原任务145继续执行、计划不变。取证后终止145，等待正常心跳确认机器人恢复IDLE/NULL，再提交任务147：三类PASS并冻结、进入监督，资源临界规则仍判HIGH，保留软风险分支。

证据：[真实占用/竞争任务与快照、事件、消息](evidence/SRS_F013-V1.144-resource-conflict-20261103.json)、[释放后空闲候选对照](evidence/SRS_F013-V1.144-idle-candidate-contrast-20261103.json)。原V1.143 F完整保留；146没有设备指令，未宣称重复下发曾发生。

## DEF-S3-093：局部重规划未传当前taskId，误拒自身占用设备

级别中，关联 `SRS_F013.R03`，映射 `TC-039.S2`、`TC-041.S2` 的资源冲突及邻接合法边界。**本缺陷在独立服务级边界测试中复现，尚未通过真实HTTP/设备端到端异常路径复现。** 原DEF-S3-092的真实外部占用修复不因此重新判失败。

V1.144新六参数校验器明确允许当前任务复用自身占用设备，修复方也新增该直接方法单测。但是生产 `ReplanningService.replan` 仍调用五参数重载：

```java
planValidationService.validate(renumberedTail, snapshotAgents,
        allowedTypes, task.getTaskFamily(), failedStepSeq - 1);
```

该重载将currentTaskId传为null。即使快照中的currentTaskId正是当前任务，生产重规划链路也把它视为外部占用并报ERR_RESOURCE_CONFLICT。

独立测试执行真实ReplanningService和真实PlanValidationService，仅mock存储、快照提供者、模型和风险边界；构造字段完整且模型成功返回的单步重规划，快照代理ONLINE/BUSY、拥有任务ID与当前任务相同（例如步骤超时后代理尚保留该任务占用）。三项对照：

| 独立服务测试 | 结果 |
| --- | --- |
| 同一任务快照直接调用六参数真实校验器，传入当前taskId | P，整体通过 |
| 同一快照经过生产ReplanningService入口，期望同样通过并冻结新版本 | **F**：约束为FAIL，错误“已被其他任务占用”，ERR_RESOURCE_CONFLICT |
| 代理实际属于不同任务，经过生产ReplanningService入口 | P，继续约束FAIL且未冻结，ERR_RESOURCE_CONFLICT |

这两项对照区分了新校验器本身与生产调用参数丢失；失败不是模型缺字段、测试编译错误或外部资源冲突夹具。原计划步骤保持不变。测试断言在约束误判处失败，没有把后续设备执行效果写成已实测。

证据：[独立测试源码](fixtures/IndependentF013OwnedReplanV144Test.java)、[原始Surefire失败结果](evidence/SRS_F013-V1.144-independent-owned-replan-results-20261103.txt)、[完整测试输出及调用点/环境](evidence/SRS_F013-V1.144-environment-and-owned-replan-diagnostics-20261103.json)。本轮合计22项：修复方专项18＋Spring上下文1均通过；独立3项中2P/1F，合计21P/1F/0错误。没有将修复方308项全量回归声明改写为本轮GPT实测。

请在真实重规划链路显式传递当前taskId并保留已完成步骤前缀参数，同时核对其他初次规划/基线/重规划调用点。继续硬拒其他任务占用，维持自身占用例外；用生产服务入口测试，不能仅再次验证六参数方法的直接调用。

## 覆盖与剩余范围

- R03仍为F，现由DEF-S3-093支撑；原DEF-S3-092关闭且失败证据不删除。TC-039.S2/041.S2保留历史实际结果并追加本轮外部占用通过与服务级自身误判F。
- 前端未改变，DEF-S3-091沿用V1.143真实浏览器证据，保留 `3d3e911e0dd3ba39753ee665b4d59eb5ae42ce63` 来源。V1.142中结构/错误汇总、强行放行和事件等原P继续保留原版本，不复制为V1.144新增实测；新约束改动的专项回归、外部占用和空闲对照已在本轮执行。其余历史复用范围需在最终收口继续审查。
- 合规超规行李四渠道/时序、离线与类型越界、基线二次校验、手动失败、冻结与局部新版本剩余断言未完成，保持NT；没有因关闭单个缺陷而宣布整项通过。

## 环境与清理

GPT schema `tip_gpt_f006_v118_20261030`、Redis10、后端18129、模型18117、机器人18132；本轮未开前端/浏览器。资源规则恢复启用、仿真器SUCCESS；145已终止，146/147保留待人工，无活跃夹具分配，机器人最终ENABLED/ONLINE/IDLE/NULL。三自有进程停止，18129/18117/18132/15179均释放。独立测试曾临时复制到backend测试目录运行，核对与受控源码哈希一致后移除临时测试源文件及单个编译产物；受控源码和失败结果永久保留，没有修改产品代码。

资源探针继承了V1.143的404说明字符串，当前原始证据已追加更正：该404仅发生在V1.143，V1.144首次即使用正确URL；本轮原始观察与断言没有改写。[环境/清理与更正说明](evidence/SRS_F013-V1.144-environment-and-owned-replan-diagnostics-20261103.json)、[实际模型请求](evidence/SRS_F013-V1.144-model-requests-20261103.jsonl)。未触碰Claude资源、未上传凭据或原始Office资料。

下一步：Claude先fetch并合入最新origin/ai/gpt-test，修复DEF-S3-093及相关调用参数，提交下一唯一V1.N标签后交回；GPT先复测该服务边界并尽可能补真实异常入口，再续测F013剩余范围。整项通过后才合main。
