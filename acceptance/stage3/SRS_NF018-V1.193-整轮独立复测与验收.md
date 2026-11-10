# SRS_NF018 V1.193 独立复测报告（2026-11-10）

- 产品：V1.193 / d9ac610515168208ca5f78ef3a40f308f69d81d2；隔离环境：127.0.0.1:18130，schema `tip_gpt_nf018_v193_20261110`，Redis db 11。
- 结论：**SRS_NF018.R01 = 0P/0F/1NT；NT-S3-025 未关闭。** 未合入 main。

## 技术观测（P）
- GET /actuator/prometheus → 200，text/plain，含 # HELP/# TYPE，jvm_*、process_*、system_cpu_usage、http_server_requests_seconds_*、hikaricp_connections_* 均存在；/actuator/health=UP，/actuator/metrics=200。证据：`SRS_NF018-V1.193-prometheus-sample-20261110.json`、`...-raw-20261110.txt`，探针 `probe-nf018-v193.py`，启动 `fixtures/start-nf018-v193-jar.py`（未覆盖应用自身 management 暴露配置）。

## 未通过原因（NT）
- 五方职责凭据：V1.193 新增两份文档由开发侧编写，人名/签章为文本占位（[已签署：…]），不能证明开发团队支持责任已被接收，也不能证明月之暗面实际作出可用性/固定版本/故障恢复承诺。`retest-maintenance-handover.py` 复跑结果两项验证均为 false。
- 不放宽标准。关闭路径：真实签收/承诺记录，或经 BASELINE_CHANGES 裁决后重测。
