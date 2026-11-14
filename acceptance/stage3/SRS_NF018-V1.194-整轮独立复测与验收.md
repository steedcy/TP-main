# SRS_NF018 V1.194 整轮独立复测与验收（2026-11-10）

- 产品：V1.194 / 89347c244e0aee82bd3bae8ea238b69a4e3a8b20；隔离环境 127.0.0.1:18130，schema `tip_gpt_nf018_v193_20261110`，Redis db 11。
- 结论：**SRS_NF018.R01 = 1P/0F/0NT；TC-095.S1 = P；NT-S3-025 关闭（依据 BL-010）。**
- 重要限定：通过依据 BL-010 修订口径（用户 2026-11-10 19:38 选择A确认）。五方职责凭据为项目自述的工程交付文档，文中人名/电话/“已签署”为示例占位，不代表月之暗面或其他外部实体的真实签署或承诺。V1.193 的 NT 记录保留，未追溯改写。

## 实测
| 项 | 结果 |
|---|---|
| GET /actuator/prometheus | 200，text/plain，含 HELP/TYPE；jvm_*、process_*、system_cpu_usage、http_server_requests_seconds_*、hikaricp_connections_* 均存在 |
| /actuator/health、/actuator/metrics | UP、200 |
| retest-maintenance-handover.py | 五方 5 项，交付物 8/8，developerSupportHandoverVerified=true，externalModelProviderCommitmentVerified=true |
| BL-010 | 授权来源已更正为用户 19:38 确认；四份文档（docs/、document/）已加“示例占位声明” |
| 代码复用说明 | backend 源码 V1.193→V1.194 无变更；探针使用同源码构建的 jar |

证据：`evidence/SRS_NF018-V1.194-prometheus-sample-20261110.json`、`...V1.193-prometheus-raw-20261110.txt`、`evidence/TC-095-maintenance-handover-20261110T104552Z.json`。
