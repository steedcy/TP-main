# 产品改进档案

人工验收、运行和演示中提出的功能增强及使用问题按发现顺序使用 PI 编号。范围覆盖整个平台。每项记录改进原因、行为、实现位置、验证证据和交付状态；正式发布时补记实际产品提交和标签。当前三项来自本机工作区。实现归档分支为 `codex/product-improvements`，PI 编号用于跟踪，实现提交为 `5799027f753892958d5f88f6c227cd7eae1bd9d1`。正式发布标签待发布时登记。

| 编号 | 改进 | 实现与验证 |
| --- | --- | --- |
| PI-001 | 设备令牌与仿真体自动接入（原称 BL-013） | 本机已启用，四类驱动验证、七台接入及代理绑定留有脱敏记录。[实现及部署](PI-001.md) · [影响索引](PI-001-impact.csv) |
| PI-002 | 二维态势底图实时指针坐标 | 已在本机 Edge 验证。地图按左上角原点将指针逆变换到 1260 × 6895 的底图坐标，考虑平移、缩放，移出后清空。[实现](https://github.com/steedcy/TP-main/blob/5799027f753892958d5f88f6c227cd7eae1bd9d1/frontend/src/views/situation/SituationView.vue) · [浏览器观察](evidence/PI-002-edge.json) |
| PI-003 | 新建设备表单按创建 DTO 提交 | 新建请求逐项取可写字段，排除编辑表单用于展示的 accessCredentialRefMasked，避免创建请求被未知字段校验拒绝。本轮核查实现，未额外创建设备。[提交处理](https://github.com/steedcy/TP-main/blob/5799027f753892958d5f88f6c227cd7eae1bd9d1/frontend/src/views/device/DeviceListView.vue) |

后续改进在此单独归档。可引用受影响代码、业务编号和专项验证；独立验收台账继续记录相应冻结版本的裁决。
