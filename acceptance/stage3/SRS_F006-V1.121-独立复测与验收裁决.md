# F006A/F006 V1.121独立复测与验收裁决

结论：**REQUIREMENT_PASSED（V2.3）**。本组TC-017～022共6编号、15步骤和21规则完成复合验收；无剩余产品F/NT。当前产品/标签V1.121=`91a63b67ea7220da3086d61f74cbca083a7f89e1`，Claude交接debdd759f03fda7ff73dc04847d2b0e319f9409a；接收检查点68fffdd。整个平台95编号尚未全部验收。

## 当前实测与历史覆盖

本版28个完成的组合观察P28/产品F0，不是28项用例。原始清单见`evidence/SRS_F006-V1.121-build-and-summary.json`。V120/b0f917c的33个API观察及V119/62d9582门禁正向观察按影响复核引用，保留原测试SHA，未冒充V121重新实测。完整21规则映射见stage0 `F006-规则执行映射-V2.3.csv`；中心steps/rules记录本组复合裁决。更新前F/NT/P登记另存`...-prior-register.json`，旧原始失败证据全部保留。

- **DEF-S3-081关闭**：真实Edge编辑G119_LIVE，改名及输入默认值，白名单PUT200；编码/类型不可改；表单关闭、状态未测试、启用被禁止；实际代理重测显示请求/响应/耗时后启用成功。模板编辑同样200，UI可追溯V1.0/V1.1不可变历史。证据ui、ui-rest、template-history及test-modal。
- 类型矩阵40格与受控正文预期、当前API、当前UI及V120原始xlsx全部一致。实际用本机.xlsx关联程序LibreOffice Calc打开，五行八能力数据正常、没有修复提示；Microsoft Excel未安装，不声称微软客户端实测。Excel格式导出符合原TC017口径，无需求内容变更。证据matrix-compare、matrix-ui、calc-open。
- 模板全部有效候选自动加载供选、停用项排除；真实页面预填、定制默认值并保存未测试。未使用模板取消删除保留、确认删除后移除；实例空/长/重名/越界/未知能力/参数空名空类型12类拒绝，有效最大长度接受。停用模板已引用实例继续真实代理调用成功。证据template-options、prefill-r2、delete-ui、close-gaps及final-read审计。
- 在用能力停用：同设备仍有同类能力时原任务继续；最后能力停用后切换候选仿真器18131，真实回调完成任务、无重规划；无候选时恢复失败先于唯一重规划，受控模型失败后转人工并释放原代理。采用自有schema合成已在执行的任务/计划/占用前置，不宣称替代从任务创建开始的完整E2E。证据recovery、no-candidate。
- 真实3秒HTTP读取超时：测试结果FAILED、记录原因、约3030ms、启用400。V119设备拒绝/参数非法/未测试门禁沿用五个完全一致服务/DTO/传输源码blob；V120 V22旧绕过隔离、有效记录保留、候选及命令过滤保留原SHA。V121进一步实测全平台exists拒绝无证ENABLED、真实测试通过后接受。证据remaining-api、fullplatform、impact-review。
- 全局400变更覆盖能力/模板未知字段及其他接口畸形JSON，不回显合成敏感值；F003/4/5设备身份/代理启用在线/心跳阈值30和四类画像冒烟通过；真实启动Flyway21/22不重放。证据neighbor。

## 构建、探针及边界

GPT独立后端隔离构建成功（约1分35秒，package时跳过单测，未计为单测P）；本版前端Vite生产构建成功，输出自有.local-test目录；UI/API运行的是V121源码。Claude报告178单测/2旧跳过属于Claude定向验证，未计独立P。构建摘要和jar摘要见build-and-summary。

以下原始false属于探针而非产品失败，均保留并逐项裁决于impact-review：全平台exists最初使用不存在的SPECIAL_ASSISTANCE任务定义，正确提前400，改注册的SPECIAL_PASSENGER_SERVICE后补齐目标分支；autoload最初错误比较实体能力表，原TC018.S3实际要求加载有效模板**供选择**，已逐项比较四个下拉候选；首次超时探针误读DTO没有的testPassed，读取失败也未保留瞬态duration，仅补一次缺失原始POST；UI分页/模板夹具/placeholder遮挡中断均只恢复缺口。不得把这些原始探针false隐藏为P，也不把它们当产品F；没有为失败放宽业务标准。

无需求或用例语义删改，本次仅按已生效BL-002建立F006执行共证映射。历史覆盖、当前实测与探针诊断分开报告。最终95编号缺口收口及三核心完整端到端场景仍须在后续完成。

## 交接与环境

本轮证据、登记及验收报告提交推送后，以HANDOFF最新REQUIREMENT_PASSED记录为准；main快进并核对远端后，Claude从main同步，继续SRS_F007，不再重复F006全套。标签V1.121继续指向原已验证产品，不移动。

GPT独立资源schema tip_gpt_f006_v118_20261030/V22，后端18129/Redis10（PID11564，操作前核对）、主仿真器18130、替代仿真器18131、Vite15179。受控18132超时夹具和18117模型已停止/还原；未覆盖schema。用户未提交document/及旧Vite配置未动。下一需求应新建隔离夹具或明确复用，不运行首次建库脚本覆盖旧F记录。
