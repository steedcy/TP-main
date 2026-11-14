# SRS_F015 V1.156 整轮独立验收与裁决

2026-11-04开工并完成业务采证，2026-11-05归档及合入；Asia/Shanghai（UTC+08:00），证据文件日期保留开工日。按V2.4 / BL-005完整执行当前需求全部适用项，预期依据stage0正式逐步口径、规则矩阵、V2.3澄清及V2.4执行补充；业务标准未改。

**REQUIREMENT_PASSED：规则9P/0F/0NT，步骤6P/0F/0NT。DEF-S3-066、098本轮关闭；065、067、096、097有当前回归并保持关闭。** 本轮没有历史业务P替代当前需求覆盖。证据先提交推送，随后安全合入main并以最终HANDOFF记录远端实际SHA；本报告本身不代替Git合入凭证。F016另启动，本结论不代表后续需求、三核心场景或95项整体验收通过。

## 产品版本核对及范围

- 实际待测产品：**V1.156 → `5effea7e267f5ef724a00a58716c67a59b284272`**；实际Claude交接提交 **`ee77957e776b5985393f1263d605905035bdacea`**，READY_FOR_GPT。`ai/gpt-test`从868c150安全快进接收该交接，保留全部旧证据；产品树与V1.156完全相同，GPT未修改产品。
- 交接消息和文档把完整SHA写成`5effea7e267f5ef724a00a58716c67a59b284272`、`ee779579ba6c5a083a218cf5962779a1f0a2ba03`；两个对象实际均不存在。已fetch并用远端refs、cat-file、真实祖先/提交说明及两缺陷代码差异查明是完整SHA文字错误，七位前缀相同；固定测试用户明确指定的实际远端标签V1.156，开测前已说明，未猜版本、未移动标签。原声明保留，核对原始输出见version-alignment JSON；最新交接入口更正为真实完整SHA。
- 上项F014已验收并合入main，开工远端main=`7d772f83f81d0cd589dc2db6fd622a65658810a5`。主工作区仅在本需求全部通过后安全同步main；用户改动与未跟踪文件保留。
- 本轮变更是异常恢复确认时机、候选穷尽排除集以及两处只读弹窗版本格式；直接依赖覆盖基线模板生命周期/选择/冻结、生产Spring容器注入、监督降级及自主重规划。ROADMAP中“待移植”的F020/F021等暂存改动未视为交付，也没有为了验收它们扩大F015范围；相关恢复与模板UI通过真实运行确认实际交付。

## 当前逐项验收

| 规则 | 当前 | 独立证据与断言 |
| --- | --- | --- |
| R01 | P | 267高风险原自主V1无分配，已真实试运行/启用模板经校验接管生成基线V2并完成 |
| R02 | P | 267高风险、268无效规划JSON、269规划服务503、270理解服务503、274真实校验页“转基线执行”分别执行，自动选择且无需人工挑选模板 |
| R03 | P | 各降级原始taskGoal不变，仅替换来源/步骤，API与持久计划一致 |
| R04 | P | 合法1步及285五步三类PASS/冻结并执行；271能力FAIL、272约束FAIL、286存储六步结构FAIL均未冻结、零设备指令、待人工；静态0步/6步API400且模板数不变 |
| R05 | P | 273匹配候选停用、292真正零模板任务族、三类再校验失败均有原因并安全人工，不执行原高风险候选 |
| R06 | P | 原计划/模板冻结版本/降级原因持久记录完整；真实Edge固定来源、多维依据、原计划链接与只读入口通过；两弹窗V1.0及编辑后的V1.1精确显示，098关闭 |
| R07 | P | 280精确族2步优先于前缀族1步；294证明前缀族实际可用；278少步骤优先于更近试运行；283反向启用仍选282较晚成功试运行B，选择依据时间与DRY_RUN_SUCCEEDED精确一致 |
| R08 | P | 288切换后真实成功才确认恢复；289两候选真实FAILED后直接人工、仅基线V1、无重规划/二次降级，无假恢复事件且异常全FAILED/RESOLVED；切换中PROCESSING/null |
| R09 | P | 290实际EXECUTING时将模板V1.0改V1.1/DRAFT及完成条件，冻结计划前后完全相同，仍按旧条件完成；UI明确区分冻结版/当前版 |

| 关联步骤 | 当前 | 范围 |
| --- | --- | --- |
| TC-047.S1 | P | 四类入口，规划错误与两类模型故障独立观察，真实UI转模板 |
| TC-047.S2 | P | 三个排序维度、事件依据及非精确候选合法对照 |
| TC-048.S1 | P | 合法三类校验、三类硬拒绝、关联/原因留痕、冻结与执行中编辑 |
| TC-048.S2 | P | 原目标/计划来源/模板版本追溯、只读详情与角色权限、多维依据、冻结版本保护 |
| TC-049.S1 | P | 停用、真零匹配、所选模板再校验失败安全人工 |
| TC-050.S1 | P | 多候选恢复成功/穷尽对照、禁止重规划/二次降级、异常/事件如实留痕 |

邻接TC-059.S2当前恢复结果/影响结论观察通过；TC-063.S2仅追加当前计划/模板/恢复时间线观察，保留其完整生命周期旧F，不提前宣称F018/F020整项通过。291自主失败仍能用一次重规划，确认基线禁止重规划没有误伤自主分支。

## 缺陷关闭证据

**066**：保留V1.155任务261假成功原证据，当前288/289完整复测同类真实双候选原反例及合法对照。第一台AGT-803437A3均有两次EXECUTE_CAPABILITY实际FAILED反馈；替换设备AGT-D46B6787在288真实SUCCESS，在289真实两次FAILED，核对实际设备指令回执，不只看候选列表或分配文字。

两任务都捕获切换中异常PROCESSING、recovery_result=null且无EXCEPTION_RECOVERED。288实际步骤完成后，异常36才SUCCESS/RESOLVED，恢复事件时间23:56:02.405471不早于成功反馈持久时间与STEP_COMPLETED。289异常37/38最终全部FAILED/RESOLVED，resolved_at非空，无EXCEPTION_RECOVERED；任务待人工，有状态转移与原因，计划仍唯一BASELINE_TEMPLATE V1，replanUsed=false。异常类型、步骤、原因、恢复动作、结果、影响结论、解决人/时间均有持久记录。离线验证器只读取原观察补充断言，不新增任务或实测次数。

**098**：Edge真实操作任务267“查看详情”、模板列表名称/“查看”及query直达，均呈现完整只读参数映射，模板版本精确为API的V1.0。290编辑模板后的当前详情精确为V1.1，冻结引用仍V1.0，页面区分两者。操作员无编辑控件，GET200/PUT403；配置管理员只读/可编辑对照均通过，未保存管理员编辑对照。原V1.155的VV1.0/VV1.1 DOM及PNG保留。

065多候选穷尽无重规划、067原39号与当前模板只读入口、096实际JAR启动、097反向启用及精确试运行时间，均有本轮当前观察，不仅引用历史关闭结论。本轮无新增产品F或NT。

## 测试层级、环境及重跑

- GPT自有worktree=`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`，分支`ai/gpt-test`；PG schema=`tip_gpt_f006_v118_20261030`，RedisDB10，生产JAR18129/外部受控模型HTTP18117/自有仿真器18132与18133/Vite15179。没有触碰Claude资源或对共享服务注入故障。
- 29个真实任务266～294＝**10个真实成功试运行＋19个独立正式业务观察**，没有上一轮242式重复等价类。每次观察映射多规则不增加次数。真实HTTP连接生产解析/校验/选择/持久计划与事件/设备网关及双仿真设备；模型返回受控内容/503，不声称真实大模型质量或真实设备覆盖。
- 270提交为HTTP503/业务4113，任务已持久化并成功执行合格基线，按异常分支裁决；其余正式提交HTTP200/业务200。失败类核对计划冻结、任务状态、零指令与原因，而非只看HTTP。
- 当前8套件 **43项，0失败/错误/跳过**；后端生产package与前端build（3269模块）成功。实际启动本轮打包JAR，health=UP，认证后任务/总览/代理入口通过，JAR SHA256见总核对JSON。Claude全量345项不是GPT本轮执行数量。
- Edge156.0.4314.58无头真实登录/点击当前前端源码，全部UI断言通过，无JavaScript页面错误。生产前端构建另有原始日志；无原生Windows可视浏览器/实体设备覆盖声明。

```text
backend: mvn -o -Dtest=TaskExceptionServiceSpringContextTest,BaselineDowngradeAndFailureBoundaryF015Test,BaselineDryRunLifecycleTest,BaselineTemplateF008Test,BaselineDowngradeBindingF008Test,BaselineFailureNoReplanF015Test,RecoveryEventTruthF015Test,ReplanningHighRiskDowngradeTest test
backend: mvn -o package -DskipTests
frontend: npm run build
python .local-test/launch156-model.py
python .local-test/start156.py
python .local-test/launch-robot156.py
python .local-test/launch156-vite.py
python acceptance/stage3/probe-f015-v156.py
python acceptance/stage3/probe-f015-v156-supplement.py
python acceptance/stage3/probe-f015-v156-prefix-control.py
python acceptance/stage3/verify-f015-v156-recovery.py
```

主探针自动调用`retest-f015-v156-ui.cjs manual <taskId>|frozen|details`。隔离启动等价助手保存为`fixtures/start-f015-v156-jar.py`；模型`fixtures/f015-v156-controlled-model.py`。私有DB/DPAPI/测试账号配置沿用本机已有助手，仅本地读取，不提交凭据。启动环境固定上述schema/Redis10，PLANNING_MODEL_PROVIDER=external、endpoint18117、设备回调18129，额外故障注入模式为空。须先确认资源归属和端口空闲；历史文件存在时探针拒绝覆盖，新轮用新标签/路径。代码继承已修正的夹具顺序与任务定义payload，本轮无探针诊断或前置缺口。

## 清理与证据索引

本轮SQL写夹具仅为新合成前缀族定义、对自有真实五步试运行模板故意写六步再精确恢复，未改产品校验或共享服务；其余创建/试运行/启用/编辑/业务执行走真实API。主导航能力已恢复启用，规则状态恢复，全部本轮模板/定义停用，B设备/能力/agent停用。失败任务保留原观察/版本后以明确清理原因终止。

266～294无活跃分配，agent无current_task_id；历史7条旧待分配记录保留。收尾占位行检查为空，无额外SQL分配清理。5个自有进程树核对命令后停止，18129/18117/18132/18133/18134/18135/15179无监听，无无头Edge残留。日志生成的Spring开发密码已脱敏，原日志留本机；无Office原件、真实隐私或凭据入库。

| 文件（均在acceptance/stage3/） | 内容 |
| --- | --- |
| `evidence/SRS_F015-V1.156-complete-verification-20261104.json` | 完整SHA/JAR哈希、健康/核心冒烟、全部规则步骤、任务计数、权限、配置恢复/端口停机、单测套件 |
| `evidence/SRS_F015-V1.156-full-round-20261104*.json` | 主轮、零匹配/边界补充、前缀合法对照；原始任务/计划/事件/SQL/指令和断言 |
| `evidence/SRS_F015-V1.156-recovery-command-verification-20261104.json` | 原始文件SHA256、两设备真实反馈与异常终态/恢复事件次序验证，零新增业务任务 |
| `evidence/SRS_F015-V1.156-ui-*-20261104.json/png` | 当前真实浏览器DOM、断言及截图 |
| `evidence/SRS_F015-V1.156-*-20261104.txt` | 定向测试/package/前端build/实际JAR脱敏日志 |
| `evidence/SRS_F015-V1.156-model-requests-20261104.jsonl` | 受控模型真实HTTP请求轨迹，虚构任务数据 |
| `evidence/SRS_F015-V1.156-version-alignment-20261104.json` | SHA文字错误的原声明、远端实际refs及查明结论 |
| `evidence/SRS_F015-V1.156-ledger-before-20261104.json` | 更新前规则/步骤/缺陷原记录，历史F/NT保留 |
| `evidence/SRS_F015-V1.156-cleanup-placeholders-20261104.json` | 收尾无待清理占位行 |

证据提交推送、main同步及最终交接提交的实际SHA以随后HANDOFF/ROADMAP登记和远端refs为准；不修改V1.156产品标签。下一项为F016，由Claude从验收后最新main另行启动。
