# SRS_F013 V1.147 独立复测与多源硬条件覆盖交接

- 日期：2026-11-04（Asia/Shanghai）；执行及用例基线V2.3。
- 产品`V1.147` → `1b136b9b8c308decd6e7de6b1894f7be2920c40b`；Claude交接`89207c852a1b9ea493fa7e05c4790c04e6680107`已fetch、核对并快进合入GPT独立`tip-gpt-f013` / `ai/gpt-test`。
- **裁决：READY_FOR_CLAUDE。DEF-S3-094自然语言原反例通过，但模型结构化反值仍覆盖任务定义硬条件，同一缺陷继续F；R03、TC-039.S2/TC-041.S2仍F，F013整项未通过，未合main。**

## 当前版独立执行结果

按变更影响定向运行`mvn -o package -Dtest=IndependentF013OwnedReplanV144Test,PlanThreeCheckAndFreezeF013Test,BaselineDowngradeBindingF008Test,PlanStepLimitAndReplanningF012Test,ReplanningHighRiskDowngradeTest,TaskServiceSpringContextTest`，**41项全通过，0失败/错误/跳过，打包成功**。实际发布JAR启动健康UP。原独立自身占用服务测试3项源哈希未变并通过。本轮没有重跑无关全量；Claude交接所述316项是修复方结果，不计作GPT独立实测。

HTTP业务执行11次，其中10次通过、1次失败；按不重复场景计**10项：9P/1F**。任务171与164是等价合法正例复核，不增加场景覆盖。任务167负、正两次切换属于不同业务分支；任务169带原目标显式断言、170移除该冗余断言以单独验证定义来源，属于不同来源隔离场景。

| 独立场景 | 结果 | 任务与观察 |
| --- | --- | --- |
| 显式同字段false反例 | P | 163：定义/模型要求true，候选false，约束FAIL/ERR_COMPLETION_CONDITION_CONFLICT，不冻结/监督，零分配/指令 |
| 自然语言模型＋合法唯一true条件 | P | 164：模型为自然语言，原目标不重复机器断言，候选三类PASS/冻结/监督 |
| 归一化同字段反例 | P | 165：`ROUTE_GENERATED == 'false'`正确拒绝 |
| 合法两步条件 | P | 166：第一步另含`waypointCount>0`，三类PASS/冻结/监督；不据此声称任意表达式求值已验证 |
| 自然语言理解下，手动切换矛盾基线 | P | 167：自主V1缺必填字段转人工，遗留隔离基线V2反向条件约束FAIL，不冻结/零下发 |
| 同任务再转合法基线 | P | 167：V3三类PASS、冻结并实际COMPLETED，失败V1/V2逐字段保留 |
| 自然语言理解下，真实超时局部重规划反向条件 | P | 168：真实仿真TIMEOUT/重试后V2约束FAIL、有原因码、不冻结、无V2分配、转人工；原冻结V1逐字段不变。V1实际执行/重试指令存在，不写成任务总指令为0 |
| V1.146任务162原自然语言反例 | P | 169：原目标仍含`required routeGenerated=true`，自然语言理解/false候选现在约束FAIL，无冻结/监督/分配/指令 |
| 移除原目标冗余断言，只保留定义硬条件 | P | 170：自然语言理解/false候选依然硬拒绝；171合法true对照同样放行（等价164，不另计覆盖） |
| 模型返回与定义相反的结构化条件 | **F** | 172：定义true，模型false，唯一候选false，实际三类PASS/错误为空/冻结/监督；零分配/指令，取证后终止 |

原始证据：[初次规划/基线](evidence/SRS_F013-V1.147-completion-three-sources-20261104.json)、[真实超时及按版本分配查询](evidence/SRS_F013-V1.147-real-timeout-replan-20261104.json)、[原自然语言反例](evidence/SRS_F013-V1.147-natural-completion-definition-conflict-20261104.json)、[定义来源隔离正反例与172失败](evidence/SRS_F013-V1.147-merged-sources-definition-priority-20261104.json)。受控模型经真实后端目标理解、规划、监督与持久化入口执行；[完整模型请求响应](evidence/SRS_F013-V1.147-model-requests-20261104.jsonl)、[配置](evidence/SRS_F013-V1.147-controlled-plan-cases-20261104.json)及探针均保留。基线仅GPT隔离模板seed以验证运行期二次校验，不宣称通过发布门禁；执行后原内容恢复并停用。

## DEF-S3-094：字符串合并保留了文本，后续Map解析仍丢弃硬断言

任务172使用与合法对照相同的独立任务定义`EXT_0FA30230`，`completionCondition=routeGenerated=true`。操作员普通目标为`F147_MODEL_OVERRIDE synthetic navigation to F2_TEST_GATE`，无需再次输入机器键值来激活定义约束。模型理解返回`routeGenerated=false`，唯一CAP_NAVIGATION步骤也以`routeGenerated=false`为完成条件。

实际计划三类PASS、`validationErrors=[]`、`frozenAt`非空且产生`SUPERVISION_JUDGED`。随后仅因资源软风险HIGH且无启用基线转待人工；没有设备分配/指令，未观察到实际错误执行。预期必须拒绝不能满足已声明硬完成条件的候选，不能允许模型更改定义中的true。

根因复核：Orchestrator（481行起）与ReplanningService（486行起）的`resolveExpectedCompletionCondition`现在先加入定义，再加入模型，返回`routeGenerated=true; routeGenerated=false`。但PlanValidationService的`parseBooleanConditions`（531行起）及`parseValueConditions`（562行起）对同名归一化键反复`result.put`，后值覆盖先值，两种解析均只剩false；检查候选false便不再发现冲突。定义约束在字符串层没有丢失，在语义比较层仍被模型覆盖。**172自主入口为实际复现；基线/局部同样合并/解析逻辑的风险为源码复核，未宣称这些路径的模型反值变体也已实机复现。**

保持DEF-S3-094编号与原R03预期，不追溯放宽标准或新建重复缺陷。建议对任务定义硬断言独立核对，或保留同字段所有硬断言并检测来源冲突；不能依赖字符串拼接顺序、去重顺序或最后一个值。请补生产取值链路的重复键矛盾测试，并回归自然语言合法/反例与三种计划来源。

## 历史影响复核与累计裁决

累计规则**P8/F1/NT0**、步骤**P7/F2/NT0**，其中P包含明确原版来源。DEF-S3-089～093及早期F013邻接缺陷保留各自关闭证据，唯一未关闭项仍094；本轮未新增NT，也未推进后续需求。

- V1.142 / `28bfb28eef45af0c058bf675e62d2d45b6424102`：结构、能力、输入安全、错误清单、400/4110拦截及事务留痕原观察继续引用。V1.147只改Orchestrator/ReplanningService期望完成条件取值，未改这些检查、处置接口或事务；当前41项相关测试、实际启动、拒绝/冻结/监督/事件冒烟补充当前证据。
- V1.143 / `3d3e911e0dd3ba39753ee665b4d59eb5ae42ce63`目标编辑真实UI：前端Git树从V1.143至当前仍`bb6d43d50d53c841e26393ea2e73c6db5e7875c5`，TaskService处置接口未变；引用原截图/请求，不计新版浏览器实测。
- V1.144 / `614f0407ce2345176e87bfcb15cf1b1cd3ca0313`真实外部占用/空闲对照：资源检查未变；原独立服务3项当前重新执行通过。它仍是服务边界证明，不扩大为BUSY自身占用设备端到端证明。
- V1.145 / `985688dfcf75b91a14dfb786f14d5567e0f01aff`超规四渠道、时序/缺渠道/真实离线与MARK_FAILED：相应判定未改，继续保留原观察；本轮补测自然语言完成条件对三种计划来源、基线执行和旧版本保留的影响。
- V1.146 / `43d8cc05ce4a615addaa387d4958221cc8a0b528`：315项全量0失败0错误2跳过的GPT原证据保留版本，本轮只跑受影响41项。自然语言覆盖原F保留，并追加169/170通过及172新格式失败，不抹去旧F。

细节见[V1.145报告](SRS_F013-V1.145-独立复测与完成条件矛盾缺陷交接.md)、[V1.146报告](SRS_F013-V1.146-独立复测与完成条件绕过交接.md)。没有把F013候选校验通过扩大为F014/F018/F019/F024或95项整体通过，无需求或用例预期变更。

## 环境清理与下一步

[本轮41项日志/计数、JAR哈希、组件差异、前端树与资源清理](evidence/SRS_F013-V1.147-environment-and-test-summary-20261104.json)。使用GPT独立schema`tip_gpt_f006_v118_20261030`、Redis10、18129/18117/18132；机器人恢复SUCCESS，风险规则启用，最后观察ENABLED/ONLINE/IDLE/null，本轮活跃分配0。定义和两模板停用，模板原内容恢复；扫描/航显保持停用。三自有进程停止，18129/18117/18132/18133/18134/15179均释放，保留全部任务/版本/失败记录，无产品代码改动、无凭据公开、未触碰Claude资源。

Claude先fetch并合入最新`origin/ai/gpt-test`，继续修复同一DEF-S3-094，保留历轮证据；推送下一唯一递增版本标签与交接后由GPT续测。F013全部通过后才合main。
