# SRS_F013 V1.141 独立复测与启动缺陷交接

- 日期：2026-11-03（Asia/Shanghai）；执行/用例基线 V2.3。
- Claude 交接 `c1d5adcdab3e2d1ef886697ea35448bdcc4ef600` 已 fetch 并快进合入 GPT 独立工作区 `tip-gpt-f013` / `ai/gpt-test`。
- **实际 Git 标签 `V1.141` → `cd92e49e4ab48ba62c454beeb073abc137eb15ce`。** Claude 交接及用户转述中的完整 SHA `cd92e49c7198bb602447aa72793740fa18536109` 为笔误；本报告以远端标签核对结果为准，不移动标签，原交接文字保留供追踪。
- **裁决：READY_FOR_CLAUDE。V1.141 发布物启动检查 F（DEF-S3-090），F013 未验收通过。** DEF-S3-089 的真实 HTTP/持久化复测及 F013 剩余业务范围本版均 NT，不能因修复方单测通过而关闭缺陷。

## DEF-S3-090：新增构造函数导致 TaskService 无法被 Spring 实例化

级别高；阻断 `TC-040.S2`、`TC-041.S3`、`SRS_F013.R07` 及 F013 全部业务复测。

1. 从已接收 V1.141 源码在 GPT 工作区执行 `mvn -o package -DskipTests`，构建成功，生成 `backend/target/airport-ai-app-1.0.0.jar`。
2. 使用 GPT 原有隔离配置 `java -jar` 启动：schema `tip_gpt_f006_v118_20261030`、Redis DB10、后端18129；未修改产品代码、数据库约束或应用类。
3. Flyway V27 成功执行，数据库约束已允许 `INTERCEPTED`。
4. Spring 创建 `baselineDryRunService` 依赖的 `taskService` 时失败并退出：`Failed to instantiate [com.airport.ai.task.TaskService]: No default constructor found`；根因 `NoSuchMethodException: com.airport.ai.task.TaskService.<init>()`。
5. 使用同一发布物和配置第二次完整启动，再次复现相同错误。健康检查连接被拒，无法发送业务请求。

代码复核：`TaskService` 新增带 `ForceBypassAuditRecorder` 的13参数构造函数，同时保留12参数构造函数；两个都是 public，均未指定 `@Autowired`，也没有默认构造函数。Spring 无法选择注入构造函数。旧版单构造函数自动注入的条件已不成立。请修复构造函数选择，并确保实际注入的是 Spring 管理的 `ForceBypassAuditRecorder` 代理，以保持 `REQUIRES_NEW` 生效；不能用手动 new 的兼容路径替代真实事务代理。

定向 `mvn -o test -Dtest=PlanThreeCheckAndFreezeF013Test` **15 项通过，0失败/错误**。该套件直接构造对象并使用mock，没有验证真实 Spring 上下文启动，不能据此宣称发布物可运行。建议修复后至少启动实际打包应用并检查健康，再交付。

## 原始证据和 P/F/NT

- [第一次启动完整日志](evidence/SRS_F013-V1.141-startup-attempt1-20261103.txt)、[第二次启动完整日志](evidence/SRS_F013-V1.141-startup-attempt2-20261103.txt)。
- [实际 SHA、JAR 摘要、构建/单测原始输出、迁移/约束、健康与清理检查](evidence/SRS_F013-V1.141-startup-diagnostics-20261103.json)。
- [已准备的真实 HTTP/持久化复测探针](probe-f013-v141.py)：此次在登录前连接被拒，**没有产生成功业务观察**，不计为4110或留痕通过证据。

| 范围 | 本版结果 |
| --- | --- |
| 离线打包；15项定向单测；Flyway V27及INTERCEPTED约束 | 子检查通过，不代表需求通过 |
| 实际发布物完整启动（两次） | F / DEF-S3-090 |
| DEF-S3-089：两失败候选×FORCE_RELEASE/REQUEST_SUPERVISION、4110、事件/审计持久化 | NT；应用未启动。V1.140 原F保留，尚不关闭 |
| TC-039.S1/S2、TC-040.S1/S2、TC-041.S1–S3、TC-042.S1/S2，R01–R09完整业务覆盖 | NT（本版）；历史累计台账保持原版本和来源 |

未启动模型、机器人或浏览器，未做业务数据变更。两个后端进程均因应用初始化失败自行退出；18129/18117/18132均释放。任务118/119仍待人工、零分配/指令、零拦截事件，未冒写本版P。未触碰Claude资源、共享服务故障注入或main。

## 交还后待办

Claude先 fetch 并将最新 `origin/ai/gpt-test` 合入修复分支，保留本轮及 V1.140 证据。修复 DEF-S3-090，使用真实 Spring 启动确认构造函数注入和事务代理；提交下一唯一 V1.N 标签及实际完整 SHA 后交回 GPT。GPT 先验证 DEF-S3-089 的 HTTP400/4110 和两类记录持久化，再续测合规行李、结构/能力/约束边界、修改目标重试、基线再次三类校验、手动失败、详情页错误清单和冻结不可变性。仅 F013 全部通过后合入 main，本轮不推进 F014。
