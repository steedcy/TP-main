# SRS_F013 V1.145 独立复测与完成条件矛盾缺陷交接

- 日期：2026-11-03（Asia/Shanghai）；执行/用例基线V2.3。
- 标签 `V1.145` → `985688dfcf75b91a14dfb786f14d5567e0f01aff`，Claude交接 `96814809c3013d2528b972af7576a866fc07a696` 已fetch并快进合入GPT独立 `tip-gpt-f013` / `ai/gpt-test`。
- **裁决：READY_FOR_CLAUDE。DEF-S3-093通过；新DEF-S3-094（完成条件与明确目标相反仍三类PASS）使R03、TC-039.S2/TC-041.S2为F，F013整项未通过。** 其余本轮已补断言与历史复用范围见下，不推进F014或main。

## DEF-S3-093及局部版本复测通过

从本版源码定向测试并生产打包，36项全部通过、0失败/错误；包含原GPT独立测试3项，受控源码与已纳入backend的源文件哈希一致，没有放宽原断言。自身占用生产服务入口通过，不同任务占用继续拒绝。

真实仿真器TIMEOUT触发任务150的重试与局部重规划，生成冻结V2、没有ERR_RESOURCE_CONFLICT，原冻结V1完整逐字段不变。**两份真实快照中的代理均为IDLE/currentTaskId=null，因此它证明真实异常入口及新版本链路可运行，不是BUSY自身占用例外的设备端到端证明；后者由原独立服务3项测试覆盖。**

证据：[36项测试/打包、哈希、环境与清理](evidence/SRS_F013-V1.145-environment-and-test-summary-20261103.json)、[原独立3项结果](evidence/SRS_F013-V1.145-owned-replan-results-20261103.txt)、[真实超时重规划](evidence/SRS_F013-V1.145-real-timeout-replan-20261103.json)。

## 已补齐的业务分支

| 分支 | 观察及证据 |
| --- | --- |
| 手动转合法基线 | 任务148自主V1缺完成条件、待人工；运行操作员SWITCH_TO_BASELINE后，基线V2重新结构/能力/约束全部PASS、冻结并实际COMPLETED；原失败V1完整保留。 |
| 基线不安全内容二次校验 | 仅在新建的独立夹具模板中模拟遗留不安全完成条件speed=2，任务149手动转基线后约束FAIL/ERR_MOTION_SAFETY_FIELD，未冻结、零分配/指令，维持待人工。模板启用状态及遗留内容为隔离seed，**不宣称通过模板发布或试运行门禁**。 |
| 手动置失败 | 操作员给任务149提交明确虚构原因后FAILED，TASK_FAILED包含原因，计划版本保持不变。以上三项：[原始基线与处置证据](evidence/SRS_F013-V1.145-baseline-and-manual-actions-20261103.json)。 |
| 超规行李合规自主候选 | 任务151测量、报警、智慧航显CAP_INFO_DISPLAY、导航四渠道全部存在；三类PASS、冻结、进入监督。R03以外的历史DEF-S3-035渠道矛盾已通过；DEF-S3-069仅F013候选渠道部分有通过证明，F024/TC-054/072完整闭环留待相应需求。 |
| 时序、必需渠道与离线候选 | 任务152先航显后测量，ERR_BAGGAGE_BRANCH_ORDER拒绝（实际归STRUCTURE/步骤顺序错误）；153缺航显，ERR_REQUIRED_CHANNEL_MISSING；154真实扫描代理OFFLINE，ERR_NO_ONLINE_CANDIDATE。三个候选均未冻结/监督、零分配/指令。时序的实际分类如实记录，不写成constraintCheckResult=FAIL。见[超规核心矩阵](evidence/SRS_F013-V1.145-baggage-core-20261103.json)。 |
| 类型边界与能力状态 | 当前36项中的F013专项18项包括真实校验器的未知/未启用实例、OFFLINE、错设备类型候选过滤断言；并有本轮三类物理渠道与真实OFFLINE对照。没有把错类型服务边界测试写成真实设备越界配置已启用。 |

错误清单、原因码和时间线在API原始记录中均可核对。R04失败无下发、R06处置三分支及R08原冻结版本不变/局部新版本的覆盖由本轮与以下未变更历史证据合并评估，不靠单个构建结果判通过。

## DEF-S3-094：唯一候选步骤完成条件与任务定义、理解目标相反仍放行

级别高；关联 `SRS_F013.R03`、`TC-039.S2`、`TC-041.S2`。正式stage0原口径要求“满足任务族约束与完成条件”，且准备“完成条件不满足的候选”；本轮没有修改该预期。

1. 使用新建隔离导航任务定义（与任务148合法基线正例相同），其completionCondition明确为 **routeGenerated=true**。
2. 提交任务155，目标明确要求routeGenerated=true；真实目标理解结果completionCondition同样为 **routeGenerated=true**。
3. 受控规划返回唯一一步CAP_NAVIGATION，输入目的地正确、字段完整，完成条件却是 **routeGenerated=false**。这是同一Boolean字段的直接矛盾，计划没有其他动作或条件分支；不依赖任意自然语言推理。
4. 实际版本结构/能力/约束全部PASS、validationErrors为空、写入frozenAt并产生SUPERVISION_JUDGED；仅因资源临界风险HIGH且无启用基线，转待人工。
5. 预期应在约束硬校验拒绝这种明确无法满足目标完成条件的候选，给出步骤和原因码，不冻结、不监督。该任务没有设备分配或指令，**未观察到实际执行错误结果**。

证据：[任务定义、目标理解、候选唯一反向条件、三类结果/冻结/事件/指令](evidence/SRS_F013-V1.145-completion-condition-conflict-20261103.json)、[可重跑探针](probe-f013-v145-completion-conflict.py)。现有初次规划校验仅传入allowedCapabilityTypes/taskFamily，没有把任务定义及目标理解的完成条件纳入该硬检查；请同时检查自主、基线及局部重规划的一致性，并保留合法步骤完成条件与任务最终完成条件之间的合理区别。

## 历史来源、台账及环境

- V1.142 / `28bfb28eef45af0c058bf675e62d2d45b6424102` 的六字段、六步/依赖/循环/动态代码、无效参数、硬性放行与错误展示等记录保留原版本，按本轮变更只在ReplanningService传taskId的影响复核继续引用；V1.144 / `614f0407ce2345176e87bfcb15cf1b1cd3ca0313` 的外部占用/空闲硬软对照保留原来源。新增36项包含相关变更回归，不将旧观察重复计作新版实测。
- 目标编辑真实UI引用V1.143 / `3d3e911e0dd3ba39753ee665b4d59eb5ae42ce63` 的任务124截图与请求，前端Git树V1.143/V1.145均为 `bb6d43d50d53c841e26393ea2e73c6db5e7875c5`，TaskService目标编辑与处理接口也未变；本轮没有重新开浏览器或写成新UI实测。
- 累计覆盖裁决：规则R01/R02/R04–R09为P，**R03为F**；步骤除TC-039.S2、TC-041.S2为F外其余P。P包含明确标注来源的历史覆盖与本轮新实测，不表示全部观察同版重跑。当前无已知未执行的原列入F013分支；完成条件硬拒绝的F仍阻止整项验收，修复后按影响回归补测。
- GPT schema `tip_gpt_f006_v118_20261030`、Redis10、18129/18117/18132/18133/18134。新扫描/航显能力通过真实代理测试后启用；初次扫描能力测试早于首个ONLINE心跳而失败，原失败结果保留，等待ONLINE后重测通过，作为夹具就绪错误不计产品F。[夹具及初次失败/更正](evidence/SRS_F013-V1.145-core-device-fixture-20261103.json)。
- 结束：两新设备及能力、独立任务定义和两模板均停用；原基线状态恢复，风险规则启用，原机器人ENABLED/ONLINE/IDLE/NULL，无活跃夹具分配；五个自有进程停止，六个测试端口均释放。保留全部任务、版本和失败证据，未删除数据库记录，未改产品代码或触碰Claude资源。模型输入及[受控计划集合](evidence/SRS_F013-V1.145-controlled-plan-cases-20261103.json)均为虚构数据，无凭据公开。

下一步：Claude先fetch并合入最新origin/ai/gpt-test，修复DEF-S3-094，验证同字段真/假矛盾拒绝及合法正例，核对三种计划来源；推送下一唯一V1.N再交回。GPT复测完成条件与相关邻接，通过后才将F013裁为REQUIREMENT_PASSED并合main。
