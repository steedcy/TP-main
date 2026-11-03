# SRS_F013 V1.148 独立复测与候选内部矛盾交接

- 日期：2026-11-04（Asia/Shanghai）；执行/用例基线V2.3。
- 标签V1.148 → `4f801e0d8cecb8578f1429a358614d19ff6c9243`；Claude交接`b614eb97930c780952955cd75d1dbaebab9bb078`已fetch、核对并快进合入GPT独立工作区`tip-gpt-f013` / `ai/gpt-test`。
- **裁决：READY_FOR_CLAUDE。任务172原来源覆盖反例及指定合法对照已通过，但同一候选步骤内部直接相反的合取条件仍被放行，DEF-S3-094继续F。R03、TC-039.S2/TC-041.S2仍F，整项未通过，未合main。**

## 本轮实测

从当前源码运行`mvn -o package -Dtest=IndependentF013OwnedReplanV144Test,PlanThreeCheckAndFreezeF013Test,BaselineDowngradeBindingF008Test,PlanStepLimitAndReplanningF012Test,ReplanningHighRiskDowngradeTest,TaskServiceSpringContextTest`，**42项通过，0失败/错误/跳过，打包成功**。当前JAR实际启动健康UP；原独立自身占用服务3项断言源哈希未变且通过。本轮没有重跑无关全量，修复方317项结果不计GPT独立实测。

独立HTTP业务场景12项，**11P/1F**，共11个任务；任务177负、正两次基线切换分别覆盖不同分支，不重复增加同一观察的覆盖数。

| 场景 | 结果 | 任务/观察 |
| --- | --- | --- |
| 定义/理解true，唯一候选false | P | 173：约束FAIL、ERR_COMPLETION_CONDITION_CONFLICT、不冻结/监督、零分配/指令 |
| 自然语言理解＋合法唯一true候选 | P | 174：三类PASS、冻结、监督，原目标未重复机器断言 |
| 归一化反向条件 | P | 175：`ROUTE_GENERATED == 'false'`正确拒绝 |
| 合法两步及合取条件 | P | 176：第一步`routeGenerated=true and waypointCount>0`、第二步true，三类PASS/冻结/监督 |
| 自然语言理解下切矛盾基线 | P | 177：自主V1缺必填字段，手动转遗留隔离基线V2因反向条件约束FAIL，不冻结/零下发 |
| 同任务再切合法基线 | P | 177：V3三类PASS、冻结并实际COMPLETED，失败V1/V2逐字段保留 |
| 真实TIMEOUT触发局部反向重规划 | P | 178：真实设备仿真超时/重试后局部V2约束FAIL、有冲突原因码、不冻结、无V2分配、转人工；原冻结V1逐字段不变。V1实际执行/重试指令存在，不写成任务总指令为0 |
| V1.146自然语言原反例 | P | 179：原目标含显式true，理解自然语言、候选false，硬拒绝 |
| 定义单来源自然语言反例 | P | 180：原目标不含冗余机器断言，理解自然语言、候选false，仍硬拒绝 |
| V1.147任务172原反例 | P | 181：定义true、模型理解false、候选false，约束FAIL/冲突码、不冻结/监督/下发 |
| 用户指定的同场景合法对照 | P | 182：定义true、模型理解仍false、候选改true，三类PASS/冻结/监督；说明定义权威锁定实际生效 |
| 候选内部同字段相反合取 | **F** | 183：定义true，模型理解自然语言，唯一候选`routeGenerated=true and routeGenerated=false`，实际三类PASS/空错误/冻结/监督，零分配/指令 |

原始证据：[自主/基线](evidence/SRS_F013-V1.148-completion-three-sources-20261104.json)、[真实超时与按版本分配查询](evidence/SRS_F013-V1.148-real-timeout-replan-20261104.json)、[原自然语言反例](evidence/SRS_F013-V1.148-natural-completion-definition-conflict-20261104.json)、[180～183来源/候选条件对照](evidence/SRS_F013-V1.148-merged-sources-definition-priority-20261104.json)。稳定受控模型经过真实理解/规划/校验/监督/持久化入口，[完整请求响应](evidence/SRS_F013-V1.148-model-requests-20261104.jsonl)、[计划配置](evidence/SRS_F013-V1.148-controlled-plan-cases-20261104.json)及探针均受版本控制。基线只在GPT独立schema的自有模板中seed，验证运行期二次校验，不声称通过发布门禁；结束时恢复原内容并停用。

## DEF-S3-094剩余：首值优先也用于不可信候选，反向断言被忽略

183使用与合法对照相同的独立任务定义`EXT_0FA30230`，明确要求`routeGenerated=true`；模型理解为`The navigation route has been generated.`。候选只有一步CAP_NAVIGATION，输入和必填字段完整，完成条件为 **`routeGenerated=true and routeGenerated=false`**，没有条件分支或后续步骤。

实际该原文保留在冻结的`planSteps`中，结构/能力/约束全部PASS、错误为空、写入frozenAt并产生SUPERVISION_JUDGED。随后因资源软风险HIGH且无启用基线转人工；零设备分配/指令，未观察到实际错误执行，取证后已人工终止夹具任务。预期该完成条件必须被硬拒绝：同一个Boolean字段不可能同时满足true与false，后半句也与任务硬条件直接相反。这里不要求任意自然语言理解或表达式求解；前一合法对照176也使用同一`and`合取格式。

根因复核：`PlanValidationService.checkCompletionConditionConflict`对期望和步骤都调用同一组解析器。`parseBooleanConditions`（532行起）及`parseValueConditions`（554行起）本次均改为首值优先（546/567行的`!result.containsKey(key)`）。首个true锁定候选字段，后面的false被忽略，最终比较只见true。任务定义权威优先已在181/182通过，但此优先策略不能同时用来忽略候选自身的反向硬断言。

保持DEF-S3-094“完成条件反向矛盾未硬拒绝”的原编号与R03预期，不修改基线放宽失败。请区分期望来源的权威合并与候选所有断言的校验：可对候选保留同字段全部值、检测内部冲突，或在比较时逐个核对反向断言；不得只取第一个或最后一个而遗漏矛盾。补候选true/false两种排列及合法重复一致值、合法中间步骤回归。183自主入口已实机复现；基线/局部使用同一解析器的风险来自代码复核，未冒称这些路径的内部合取变体也已实机复现。

## 历史影响复核与累计范围

累计规则**P8/F1/NT0**、步骤**P7/F2/NT0**；唯一未关闭项仍094。DEF-S3-089～093及早期F013邻接缺陷保留各自关闭记录，原F不删除；本轮对172场景追加P，并记录183残留F，不以原场景通过替代整条规则。

- V1.142 / `28bfb28eef45af0c058bf675e62d2d45b6424102`：六字段/五步/依赖/循环、能力/输入/运动安全、错误清单、400/4110与真实事务审计，保持原实测日期和SHA。当前只改完成条件解析及上游取值，这些分支未改；42项定向与本轮实际启动、硬拒绝、冻结/监督、事件提供当前冒烟。
- V1.143 / `3d3e911e0dd3ba39753ee665b4d59eb5ae42ce63`：目标编辑真实UI，前端Git树至当前均为`bb6d43d50d53c841e26393ea2e73c6db5e7875c5`，TaskService处置接口未变；不新增浏览器实测计数。
- V1.144 / `614f0407ce2345176e87bfcb15cf1b1cd3ca0313`：外部真实占用/空闲对照，资源检查未变；原独立服务3项当前再次通过。自身占用精确例外仍是服务级覆盖，不扩大为BUSY自身占用设备端到端复现。
- V1.145 / `985688dfcf75b91a14dfb786f14d5567e0f01aff`：超规四渠道、时序/缺渠道/真实离线、MARK_FAILED等原分支判定未变，保留原版证据；相关完成条件依赖由本轮三来源与合法多步回归覆盖。
- V1.146 / `43d8cc05ce4a615addaa387d4958221cc8a0b528`的315项独立全量（2跳过）、V1.147 / `1b136b9b8c308decd6e7de6b1894f7be2920c40b`的41项定向保留原版来源；当前42项才是V1.148新实测，不将历史P改写为新版重跑。

历史细节见[V1.145报告](SRS_F013-V1.145-独立复测与完成条件矛盾缺陷交接.md)、[V1.146报告](SRS_F013-V1.146-独立复测与完成条件绕过交接.md)、[V1.147报告](SRS_F013-V1.147-独立复测与多源硬条件覆盖交接.md)。F013未通过，不推进F014或其他需求，也不扩大为95项全部通过；无需求/用例预期变更。

## 环境与下一步

[42项日志/计数、JAR哈希、差异、前端树、环境和清理](evidence/SRS_F013-V1.148-environment-and-test-summary-20261104.json)。GPT独立schema`tip_gpt_f006_v118_20261030`、Redis10、18129/18117/18132；机器人恢复SUCCESS、风险规则启用，最后观察ENABLED/ONLINE/IDLE/null，本轮活跃分配0。独立定义和两模板停用且模板内容恢复；扫描/航显保持停用。三自有进程停止，18129/18117/18132/18133/18134/15179全释放；保留所有任务、版本、失败证据，无产品代码修改或凭据提交，未触碰Claude资源。

Claude先fetch并合入最新`origin/ai/gpt-test`，继续修复同一DEF-S3-094的候选内部反向断言遗漏，保留历轮证据；推送下一唯一递增标签与交接后由GPT续测。F013整项通过才合main。
