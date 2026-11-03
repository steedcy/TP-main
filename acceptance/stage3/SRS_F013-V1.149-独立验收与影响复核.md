# SRS_F013 V1.149 独立验收与影响复核

- 日期：2026-11-04（Asia/Shanghai）；执行/用例基线V2.3。
- 产品标签V1.149 → `2a5090d27e39ca85b511bd5ff8b013c4dbfd9474`；Claude交接`3f9710e063558f42e3c1634d8c6cbd56cf68505d`已fetch、核对并快进合入GPT独立`tip-gpt-f013` / `ai/gpt-test`。
- **裁决：REQUIREMENT_PASSED。DEF-S3-094独立复测通过，F013累计规则9P/0F/0NT、关联步骤9P/0F/0NT。** 当前实测与经影响复核引用的历史观察分开列明；历轮F和原始证据全部保留。代码与证据合入main的实际提交凭据在HANDOFF/ROADMAP最终交接中登记，产品标签不移动。

## 当前版本实测

从本版源码执行`mvn -o package -Dtest=IndependentF013OwnedReplanV144Test,PlanThreeCheckAndFreezeF013Test,BaselineDowngradeBindingF008Test,PlanStepLimitAndReplanningF012Test,ReplanningHighRiskDowngradeTest,TaskServiceSpringContextTest`，**43项通过、0失败/错误/跳过，生产打包成功**。实际JAR启动健康UP；原GPT独立自身占用服务3项源文件哈希未变并通过。修复方318项全量结果不计为本轮GPT独立实测；V1.146独立全量315项（2跳过）保留原版来源，本轮仅执行影响回归。

**15个独立计划业务场景全部通过，另2次强行放行动作拦截及持久审计均通过。** 14个任务中，188两次基线切换是不同分支；不把同一观察映射多个规则重复计数。

| 场景 | 任务 | 当前结果 |
| --- | --- | --- |
| 显式反向候选 | 184 | 定义/理解true、候选false，约束FAIL/ERR_COMPLETION_CONDITION_CONFLICT，不冻结/监督、零分配/指令 |
| 自然语言理解＋合法唯一true | 185 | 原目标未重复机器断言；三类PASS、冻结、监督 |
| 归一化反向条件 | 186 | `ROUTE_GENERATED == 'false'`硬拒绝 |
| 合法两步/中间条件 | 187 | 第一步true且waypointCount>0、第二步true，三类PASS/冻结/监督 |
| 手动转矛盾基线 | 188 | 自主V1缺必填字段；基线V2反向完成条件被约束拒绝，不冻结/零下发 |
| 再转合法基线 | 188 | V3三类PASS、冻结并实际COMPLETED，失败V1/V2逐字段保留 |
| 真实超时局部重规划反例 | 189 | 仿真TIMEOUT/重试触发局部V2，约束FAIL/冲突码、不冻结、无V2分配、转人工，原冻结V1逐字段不变。V1实际执行/重试指令存在，不写成任务总指令为0 |
| V1.146自然语言原反例 | 190 | 原目标含显式true，理解自然语言、候选false，硬拒绝 |
| 定义单来源自然语言反例 | 191 | 原目标不重复机器断言，理解自然语言、候选false，仍硬拒绝 |
| 任务172原型 | 192 | 定义true、模型false、候选false，约束FAIL/冲突码，不冻结/监督/下发 |
| 任务172合法对照 | 193 | 定义true、模型仍false、候选true，三类PASS/冻结/监督 |
| 任务183原型 | 194 | 唯一步骤`routeGenerated=true and routeGenerated=false`，约束FAIL/冲突码，不冻结/监督/下发 |
| 任务183反向顺序 | 195 | `routeGenerated=false and routeGenerated=true`同样硬拒绝 |
| 合法重复一致值 | 196 | `routeGenerated=true and routeGenerated=true`三类PASS/冻结/监督 |
| 合法单步合取 | 197 | `routeGenerated=true and waypointCount>0`三类PASS/冻结/监督 |

对194分别执行FORCE_RELEASE、REQUEST_SUPERVISION，均HTTP400/业务码4110。每次独立查询确认新增FORCE_BYPASS_INTERCEPTED事件与FORCE_BYPASS_ATTEMPT/INTERCEPTED审计行；待人工状态、全部计划版本不变，零分配/指令。通过真实HTTP错误返回后的新请求及SQL观察证明持久化，不以mock调用替代。

原始证据：[自主及基线](evidence/SRS_F013-V1.149-completion-three-sources-20261104.json)、[真实超时/快照/按版本分配](evidence/SRS_F013-V1.149-real-timeout-replan-20261104.json)、[自然语言原反例](evidence/SRS_F013-V1.149-natural-completion-definition-conflict-20261104.json)、[来源/内部矛盾正反例及两次4110持久留痕](evidence/SRS_F013-V1.149-merged-sources-definition-priority-20261104.json)。[完整模型请求响应](evidence/SRS_F013-V1.149-model-requests-20261104.jsonl)、[配置](evidence/SRS_F013-V1.149-controlled-plan-cases-20261104.json)、模型及探针受版本控制。基线反例仅在GPT独立schema的自有模板seed，测试运行期二次校验，不声称通过模板发布门禁。

## 规则与步骤整项裁决

| 规则 | P依据（保留原实测版本） | 对应步骤 |
| --- | --- | --- |
| R01结构完整性、限额、依赖、循环/动态代码 | V1.142缺字段/六步/依赖/循环/动态代码矩阵；当前结构检查未改，43项含五步与重规划邻接回归；188结构失败前置亦留证 | TC-039.S2、TC-040.S1 |
| R02启用能力、在线候选、设备类型边界 | V1.142无效/停用能力；V1.145超规四渠道、真实OFFLINE拒绝及类型边界服务断言。查询/边界代码未改，当前F013专项及真实导航代理构成回归 | TC-041.S1 |
| R03参数、安全、资源、任务族与完成条件 | V1.142输入/安全矩阵；V1.144真实占用/释放对照；V1.145超规时序/渠道与不安全基线；当前原独立自身占用3项、15个完成条件/三来源正反例全部通过，DEF-S3-094关闭 | TC-039.S2、TC-041.S2 |
| R04失败不执行 | 当前全部反例及失败基线/局部V2无该版本分配下发；历史能力/安全失败保留原版；失败门禁未改 | TC-039.S2、TC-041.S3 |
| R05三类独立结果与错误收集 | V1.142多类同时失败矩阵与UI原证据；结构/能力及整体判定流程未改，当前各版本三类结果/原因码有新观察 | TC-040.S1 |
| R06错误展示与人工处置 | V1.143真实目标编辑UI；V1.145 MARK_FAILED含原因；当前188基线重新校验/执行。前端树和TaskService处置接口未改 | TC-042.S1 |
| R07硬失败不可监督/强放行 | 当前194两动作400/4110并实际持久留痕；V1.142三类失败8次拦截保留原版 | TC-040.S2、TC-041.S3 |
| R08冻结及版本不可变 | 当前合法自主/基线冻结；188失败旧版本、189原冻结V1均逐字段不变；真实异常入口生成独立V2 | TC-039.S1、TC-042.S2 |
| R09错误/原因码/时间线追溯 | 当前计划/校验/超时/人工/拦截事件与错误码；详情页展示引用未改前端的V1.142/143截图 | TC-040.S1、TC-042.S2 |

TC-039.S1/S2、TC-040.S1/S2、TC-041.S1/S2/S3、TC-042.S1/S2均为累计P。P表示当前需求在V2.3影响复核策略下覆盖完整，**不是九条规则/九步的每个观察都在V1.149重新执行**。DEF-S3-089～093保留各自关闭记录；DEF-S3-094历轮失败记录不删除，追加本轮通过裁决。

## 历史复用来源与当前变更影响

- V1.142 / `28bfb28eef45af0c058bf675e62d2d45b6424102`：[六字段等结构矩阵](evidence/SRS_F013-V1.142-batch-MISSING_stepGoal-to-MULTI-20261103.json)、[能力/参数/安全与合法边界](evidence/SRS_F013-V1.142-batch-GOOD-to-VALID_DEP-20261103.json)、[8次强放行持久化](evidence/SRS_F013-V1.142-hard-gate-persistence-20261103.json)。相关结构、能力、输入/运动安全、权限、事务代码在本次未变，当前43项与实际硬拒绝/留痕为核心冒烟。
- V1.143 / `3d3e911e0dd3ba39753ee665b4d59eb5ae42ce63`：[目标编辑真实UI](evidence/SRS_F013-V1.143-ui-goal-retry-20261103.json)。前端Git树至当前均`bb6d43d50d53c841e26393ea2e73c6db5e7875c5`；错误清单以数组下标为key并展示类型/步骤/描述/原因码，当前同一步多个冲突错误不产生原因码重复key。TaskService处置接口未变，不新增浏览器实测计数。
- V1.144 / `614f0407ce2345176e87bfcb15cf1b1cd3ca0313`：[真实外部占用拒绝](evidence/SRS_F013-V1.144-resource-conflict-20261103.json)、[空闲合法对照](evidence/SRS_F013-V1.144-idle-candidate-contrast-20261103.json)。资源检查未变；当前独立服务3项覆盖自身放行/外部拒绝。真实超时189的覆盖是异常入口与版本保护，不扩大为BUSY自身占用的设备端到端证明。
- V1.145 / `985688dfcf75b91a14dfb786f14d5567e0f01aff`：[超规四渠道/时序/缺渠道/真实离线](evidence/SRS_F013-V1.145-baggage-core-20261103.json)、[安全基线与人工置失败](evidence/SRS_F013-V1.145-baseline-and-manual-actions-20261103.json)。对应分支未改；当前合法多步、三种计划来源与基线执行补受影响完成条件回归。
- V1.146 / `43d8cc05ce4a615addaa387d4958221cc8a0b528`至V1.148 / `4f801e0d8cecb8578f1429a358614d19ff6c9243`的完成条件历轮F保留；V1.149仅改PlanValidationService完成条件审查与专项测试，期望来源锁定、其他三类检查、UI/资源/审计/配置均未改。本轮覆盖内部断言两种顺序、合法重复/合取以及之前的模型覆盖变体，不靠新单测单独判整项通过。

实际差异、原SHA/当前SHA、前端树、43项日志、JAR哈希、测试环境及清理见[环境与测试汇总](evidence/SRS_F013-V1.149-environment-and-test-summary-20261104.json)。没有修改需求/用例预期，未把历史F追溯改P。该裁决仅F013；DEF-S3-069的F024/TC-054/072完整闭环仍待后续需求，不等于三核心场景或95项整体验收完成。

## 环境和交接

GPT独立schema`tip_gpt_f006_v118_20261030`、Redis10、18129/18117/18132。机器人恢复SUCCESS、风险规则启用，最后观察ENABLED/ONLINE/IDLE/null；本轮活跃分配0。独立任务定义/两模板停用、模板内容恢复，扫描/航显保持停用。三自有进程停止，18129/18117/18132/18133/18134/15179均释放；所有任务、版本和失败证据保留，无产品代码修改、无凭据公开、未触碰Claude资源。

将本轮测试分支合入main并推送，保留标签V1.149指向原产品提交。下一轮Claude从最新main同步后启动SRS_F014，沿用现有缺陷/暂存移植清单；不依赖对话记忆。
