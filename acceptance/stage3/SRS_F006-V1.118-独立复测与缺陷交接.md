# SRS_F006A/F006 V1.118独立复测：未通过，交回修复

- 产品 `a82c2c96711995ddff5759e38503db28a20230f0` / V1.118；Claude交接 `5bca56555b70fbf6e25466e16d7809d1b9fcd911`，已合入GPT测试分支。执行/用例补充V2.3，需求及期望未调整。
- GPT隔离schema `tip_gpt_f006_v118_20261030`、后端18129/PID10772、Redis10；真实运行V20迁移及MyBatis新增版本写入/读取SQL。后端独立构建成功。无Claude目录/数据库/端口操作。
- 原始证据 `evidence/SRS_F006-V1.118-initial.json`：6个组合观察，P5/F1。**不是需求验收通过，不合入main，不推进F007。**

## DEF-S3-080：未测试能力通过“先停用再启用”绕过测试门禁

归属：SRS_F006.R04，TC-022.S2；相关TC-020.S2、TC-021重测时补状态转换回归。严重度高：核心测试成功前置被绕过。

前置：配置管理员，新建SMART_DISPLAY仿真体设备（无须启动仿真器），自动加载CAP_INFO_DISPLAY，初态UNTESTED、lastTestAt/testResult均空。本轮没有调用任何能力测试接口。

1. `POST /api/v1/devices/{code}/capabilities/{capabilityCode}/status {"status":"ENABLED"}`：400，符合前置门禁。
2. 同一能力POST `{"status":"DISABLED"}`：200。
3. 同一能力POST `{"status":"ENABLED"}`：**200**；GET能力列表确认状态**ENABLED**，lastTestAt和testResult仍为空。

预期：未实际测试成功的能力不因DISABLED中间状态取得启用资格。可以拒绝未测试→停用，或保留可停用行为并在再次启用时核验当前参数的有效成功测试；不能用DISABLED枚举本身代替测试成功证据。

定位供Claude参考：DeviceCapabilityService.updateStatus把DISABLED无条件视作“曾测试通过且参数未变”。实际入口可将UNTESTED/TESTED_FAILED置DISABLED，形成绕过；更新参数后UNTESTED同样存在该路径。建议同时定向覆盖首次未测、失败、编辑后重置未测、原测试通过后正常停用/重新启用；后者应按现有业务规则保留。

精确设备/能力编码、HTTP与最终字段见原始JSON。GPT不修改产品代码。按V2.3发现明确F后及时交回，没有继续制造无关重复证据。

## 已实测与未完成范围

- P：V20迁移落库；五类目录/矩阵可读；模板缺contentData返回400并点名；完整模板新建V1.0；更新V1.1及不可变旧版历史读取；未测试直接启用被拒。以上是组合观察，不代表TC017～022各步骤整项通过。
- F：上述绕过测试成功门禁。
- NT：类型边界UI/审计/导出工作簿逐格与Office兼容验证；剩余模板/画像字段边界；模板使用/停用/删除；实际代理测试响应弹窗与失败注入；能力停用后的候选及占用恢复；邻接及需求级完整裁决。旧F/NT证据不删除，旧P不复制为新版实测。
- 环境诊断：首次Git fetch TLS握手失败，重试成功；前端构建遭Node原生内存分配失败，PowerShell一次初始化失败，改用cmd执行探针成功。均为环境诊断，不交给Claude当产品缺陷；前端构建本版尚未通过，不可写成P。无需为本次真实API状态门禁F等待前端构建。

请Claude从最新ai/gpt-test同步本轮证据/交接，在自己的资源修复并定向回归，创建下一唯一递增V1.N，READY_FOR_GPT给出产品SHA、标签、V2.3和复测清单。V1.118原标签不移动；main保持已通过F005的0c3c062。
