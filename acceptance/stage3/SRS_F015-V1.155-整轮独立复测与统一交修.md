# SRS_F015 V1.155 整轮独立复测与统一交修

2026-11-04，Asia/Shanghai（UTC+08:00）。执行基线 **V2.4 / BL-005**，业务预期沿用 stage0 正式逐步口径、规则矩阵及 V2.3 补充。本轮发现 F 后继续其余独立分支，全部适用项执行完再统一交修。

**整项未通过，READY_FOR_CLAUDE：规则 7P/2F/0NT，关联步骤 4P/2F/0NT。** DEF-S3-065、067 本轮关闭；DEF-S3-066 原缺陷残留；新增低级别展示缺陷 DEF-S3-098。main 未合并，F016 不推进。本结论不代表后续需求、三核心场景或95项整体验收。

## 版本与环境

- 产品：`V1.155` → `78eb774a0546216deaa42c2fc2a5dc6ee8f661dd`；Claude 已推送交接 `be72400ab258e6749a00e930d213851eb9c5935c`，READY_FOR_GPT。接收合入 `ai/gpt-test` 的 merge 为 `f7e515d`；`git diff V1.155 -- backend frontend` 为空，GPT 未改产品。
- V2.4策略提交 `38cf7407729ea9c252c4486ced3b7eb4d4c085a9` 保留；只发生 EXECUTION_BASELINE 文档冲突，保留新产品行并保持用户最新 V2.4 执行组织。未修改业务预期以消除 F。
- 上项 F014 已验收，远端 main=`7d772f83f81d0cd589dc2db6fd622a65658810a5`。主工作区未用于测试，用户未跟踪文件未触碰。
- GPT 独立 worktree：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`，`ai/gpt-test`；PG schema=`tip_gpt_f006_v118_20261030`，Redis DB10。实际生产 JAR18129，受控外部模型HTTP18117，自有仿真器18132/18133，前端Vite15179。无共享服务故障注入，无真实设备覆盖。
- 真实浏览器：Edge156.0.4314.58，无头模式，运行当前前端源码；配置管理员与操作员实际登录/点击，未将API或源码阅读当作UI实测。生产前端构建另有原始日志。
- ROADMAP 暂存表经核对：F015 的 TaskExceptionService、基线失败边界、选择排序及只读入口实际在该产品树交付并接受测试；其余标为待移植的 F020/F021 等变更没有视为交付。终止邻接仅用于夹具清理，不提前验收 F021。

## 逐项裁决与本轮覆盖

下表均为当前固定 SHA 实测，**本轮历史业务 P 复用为0**。历史 F/NT/原文和证据保留，台账变更前快照另存。一次观察映射多个规则不增加执行次数。

| 规则 | 本轮 | 主要证据与断言 |
| --- | --- | --- |
| R01 | P | 236 高风险自主V1无分配，自动基线V2成功；使用真实静态校验/试运行通过并启用的模板 |
| R02 | P | 236高风险、237规划无效JSON、238规划服务503、239理解模型503、243真实校验页“转基线执行”均自动选择，不要求人工挑模板 |
| R03 | P | 各降级保留原始任务目标，只替换来源与步骤；API/计划记录均核对 |
| R04 | P | 合法1步及254五步三类PASS后冻结执行；240能力FAIL、257约束FAIL、255结构六步FAIL均不冻结、不下指令、转人工；创建0/6步请求400且模板数量不变 |
| R05 | P | 241停用匹配模板、258真正零候选任务族，以及240/255/257再校验失败均安全待人工、无设备执行；242与241同等价类，不充作零模板覆盖 |
| R06 | **F** | 来源固定标签、原计划链接、原因与多维依据、模板只读入口和权限均通过；新只读弹窗把API版本V1.0渲染为VV1.0，编辑后V1.1渲染为VV1.1（098） |
| R07 | P | 249精确族2步胜非精确族1步，265单独证明非精确族可匹配；247少步优先于较新试运行；252反向启用仍选更晚试运行B，选择依据时间与B任务251的DRY_RUN_SUCCEEDED精确相同 |
| R08 | **F** | 260候选切换后实际成功；261两候选都实际失败后直接人工、仅基线V1、不重规划/二次降级（065关闭），但22:34:31过早记录恢复SUCCESS，最终22:34:37仍失败（066残留） |
| R09 | P | 262实际EXECUTING时将模板V1.0改成V1.1/DRAFT并改完成条件，任务冻结计划前后完全相同，仍按V1.0原条件完成；UI区分冻结版/当前版 |

| 步骤 | 本轮 | 范围 |
| --- | --- | --- |
| TC-047.S1 | P | 全部四类入口；规划错误与模型不可用分别执行 |
| TC-047.S2 | P | 精确族、步数、最近成功试运行三个独立排序维度及选择留痕 |
| TC-048.S1 | P | 合法三类校验、三类硬拒绝、冻结、原计划关联与后台持久记录 |
| TC-048.S2 | **F** | 只读入口/多维依据/执行中模板变更均完成；098版本展示不准确 |
| TC-049.S1 | P | 真正零匹配、停用候选、再校验失败安全人工 |
| TC-050.S1 | **F** | 多候选穷尽与合法恢复均完成；066恢复结果与实际不一致 |

受影响邻接：TC-059.S2 当前 F（066）；TC-063.S2 仅追加当前计划/时间线/模板界面观察，保留其完整生命周期原 F，不宣称 F020 已验收。263自主任务仍可用一次重规划，确认基线禁止重规划没有误伤合法自主重规划。

## 待修复事实

### DEF-S3-066：候选切换过早被记为恢复成功（残留，中）

复现：两个自有机器人均在线、导航能力已实测并启用，设两者执行结果FAILED；提交唯一基线计划任务261（`multi-candidate-exhausted`），等待首设备失败、真实切换和第二设备也失败。合法对照260第一台FAILED/第二台SUCCESS，最终完成。

预期：切换指令/重新分配属于恢复尝试，须按实际承接和执行结果确认恢复成功；穷尽后人工，异常列表与事件如实反映结果。实际：261在 **22:34:31.111540** 记录 `EXCEPTION_RECOVERED/STEP_FAILED`、“结果: 成功…计划可继续执行”；持久异常27的`recovery_result=SUCCESS`。第二台随后也失败，**22:34:37.270103** 记录恢复失败，**22:34:37.280035** 转人工，异常28/29为FAILED。异常27成功结论未更正。原83同类虚假成功沿用066，避免重复编号。

已修复子项：待人工事件存在、reasonCode及影响判断留痕存在、无重规划或二次基线；这不使整条066通过。最小证据：`evidence/SRS_F015-V1.155-full-round-20261104-recovery-stable.json` 中 task261 的计划、分配、指令、events和SQL异常记录；真实260为对照。GPT没有用修复方单测替代这个失败。

### DEF-S3-098：只读详情重复模板版本前缀（新，低）

复现：操作员打开当前任务236“查看详情”，或从模板列表点击名称/“查看”，包含参数映射的只读弹窗中“模板版本”为 **VV1.0**，模板API/冻结记录为 **V1.0**；262模板编辑后弹窗为 **VV1.1**，API为 **V1.1**。预期准确展示API版本，不应重复前缀。

定位线索（只读审查，未修产品）：`BaselineTemplateView.vue:61` 与 `TaskDetailView.vue:254` 均在已有版本字段前添加字面量`V`。属于V1.155新弹窗展示回归，原067缺少入口已修复，单独编号。证据：`ui-details`的`taskModalVersionExact/listModalVersionExact=false`、`ui-frozen`的`currentVersionExact=false`及同名PNG。权限对照通过：操作员GET200、PUT403；管理员可编辑但本轮未保存对照修改。

## 数量、层级和执行命令

- GPT本轮8个定向/直接依赖/邻接后端套件 **43项，0失败/错误/跳过**；生产package和前端build通过。实际启动打包JAR，health=UP，认证后任务/总览/代理HTTP均通过。未把Claude全量单测当作本轮独立执行。
- **31个真实任务（235～265）=11个真实成功试运行+20次正式提交**；其中242重复241等价类，因此正式语义观察19个。浏览器角色/动作、静态API边界和43项单测单独计层级，不与任务相加。
- 真实HTTP→生产解析/校验/选择→持久计划/事件/异常→设备网关→双自有仿真设备；受控模型返回指定内容与503，不声称真实大模型质量或真实设备验收。
- 提交除239外为HTTP200/业务200；239理解模型故障为HTTP503/业务4113，但任务已持久化并降级完成，按该异常分支核对，没有误判探针失败。

```text
backend: mvn -o -Dtest=TaskExceptionServiceSpringContextTest,BaselineDowngradeAndFailureBoundaryF015Test,BaselineDryRunLifecycleTest,BaselineTemplateF008Test,BaselineDowngradeBindingF008Test,BaselineFailureNoReplanF015Test,RecoveryEventTruthF015Test,ReplanningHighRiskDowngradeTest test
backend: mvn -o package -DskipTests
frontend: npm run build
python .local-test/start155.py
python acceptance/stage3/probe-f015-v155.py
python acceptance/stage3/probe-f015-v155-supplement.py
python acceptance/stage3/probe-f015-v155-recovery.py stable
python acceptance/stage3/probe-f015-v155-prefix-control.py
node acceptance/stage3/retest-f015-v155-ui.cjs details
node acceptance/stage3/retest-f015-v155-ui.cjs manual 243
node acceptance/stage3/retest-f015-v155-ui.cjs frozen
```

重跑准备：沿用已有隔离DB/DPAPI/API私有配置，禁止提交凭据；JAR env为上述schema/Redis10，`PLANNING_MODEL_PROVIDER=external`、endpoint18117，adapter回调18129，故障注入模式为空。先启动`fixtures/f015-v155-controlled-model.py`与自有仿真器/Vite，再运行探针。探针通过本地既有154工具加载私有凭据；初次跑需要相同本地私有配置，可用新GPT隔离schema重建，不能接Claude库。证据文件存在时探针拒绝覆盖；新轮应新label/路径。受控模型脚本与所有探针已版本控制，启动助手的等价保存件见`fixtures/start-f015-v155-jar.py`，依赖与命令见其文件头。

## 夹具修正、清理和证据索引

环境/探针错误由GPT修正并完成缺口：任务定义更新误带不可变taskName（更新前被400拒绝）→257合法payload；242与241重复→258新零模板族；B仿真器启动/激活/agent顺序错误→明确connection PASSED、ACTIVE、agent ONLINE、能力实测后完成260～263。原诊断与空recovery文件保留，不作为产品缺陷或业务覆盖。最终无未完成夹具缺口、无NT。

仅两处SQL夹具：复制新合成前缀族定义用于优先级对照；对自有真实五步试运行模板故意存储六步以验证运行期结构硬闸门，已精确恢复原steps。其余创建/试运行/发布/编辑/执行均走真实API。风险规则未改，主机器人导航能力已恢复启用；本轮模板/定义停用，B设备/能力/agent停用；失败任务保留版本及原始失败观察后以清理原因终止。

收尾发现263终止后未绑定agent/command的待分配占位行173：保留原行/任务，再仅对自有夹具将该行置FAILED，动作另有原始记录；不将清理后的状态冒充业务结果。最终235～265无活跃分配，device_agents无current_task_id；历史7条旧待分配行原样保留。自有5进程树已逐项核对命令后停止，18129/18117/18132/18133/18134/18135/15179无监听，无残留无头Edge。未清理共享PG/Redis或他人资源。

| 证据 | 内容 |
| --- | --- |
| `evidence/SRS_F015-V1.155-complete-verification-20261104.json` | 完整SHA、JAR哈希、健康/冒烟、全部判定、任务计数、权限、恢复配置、单测清单、清理停机 |
| `evidence/SRS_F015-V1.155-full-round-20261104*.json` | 主轮、补充、稳定双机恢复/冻结、前缀合法对照；无stable后缀的recovery仅诊断 |
| `evidence/SRS_F015-V1.155-ui-*-20261104.json/png` | 真实Edge操作/DOM/截图，全部功能断言与098值差异，无JS错误 |
| `evidence/SRS_F015-V1.155-*-20261104.txt` | 43项单测、package、前端build、实际JAR日志；Spring生成开发密码已脱敏，原日志仅本机 |
| `evidence/SRS_F015-V1.155-model-requests-20261104.jsonl` | 受控模型真实HTTP请求轨迹（虚构场景） |
| `evidence/SRS_F015-V1.155-cleanup-placeholder-20261104.json` | 自有263占位行原状态与清理动作 |
| `evidence/SRS_F015-V1.155-ledger-before-20261104.json` | 更新前规则/步骤/缺陷原状态及事实/证据快照 |

下一步Claude修066的恢复确认时机/最终结论，并修098两处显示前缀；先fetch合入本轮证据及最终交接，再提交递增产品标签。下一轮GPT仍按V2.4执行当前需求全适用项；未全部P前不合main，不提前F016。实际证据提交SHA在随后单独推送的HANDOFF/ROADMAP中登记，产品标签不移动。
