# F006A/F006 V1.120独立复测与缺陷交接

结论：**READY_FOR_CLAUDE；DEF-S3-080已通过，DEF-S3-081页面编辑失败；整项未通过，未合main。** 执行/用例补充V2.3。产品b0f917c198ace8a58af6274497c56ab01586eca0/V1.120，Claude文档交接6258da4，GPT接收检查点d6a8c75。

## 本轮实测结果与范围

- `evidence/SRS_F006-V1.120-batch.json`共33组合观察全部P。`...-ui.json`另2个UI观察P，编辑探针中断；`...-ui-edit-r3.json`真实编辑观察F。共36个完成的组合观察，P35/F1，不能换算成36项用例通过。
- V21→V22真实升级隔离旧绕过记录G6_UNTESTED_134145/CAP_INFO_DISPLAY，状态转DISABLED，不再返回可用集合；升级前V119真实代理测试成功的G119_LIVE保留ENABLED。未覆盖、重测或篡改旧绕过记录。
- 自有库另建G120_POISON，受控注入ENABLED/test_passed=false，用于验证防御SQL，查询排除且TASK_ACCEPT被拒；随后恢复DISABLED并结束专用合成任务。该准备不声称是API门禁绕过。三条Mapper中查询和设备调用路径已真实执行，规划的全平台exists路径仍待邻接补测。
- 类型概览支持数、模板数、实例数与DB一致；空支持/未知能力/描述501/场景约束1001拒绝，0/1/上限接受，审计含前后值与修改人/时间。保存后还原类型边界。
- 模板空值/超长/编码字符/重复/越界/缺必填输入逐一点名/空输出拒绝，合法最大长度接受；未用模板删除成功。模板关联实例实际定制并通过统一代理测试，覆盖模板样例可用性及部分TC020；停用已用模板后新实例排除，原ENABLED能力状态与参数不变，已用模板删除409提示实际使用数1。
- 新仿真体画像含CAP_SIM_STATUS且仅继承SMART_DISPLAY的3类业务能力。类型列表UI显示五类，矩阵UI导出xlsx成功；原始OpenXML尺寸及数据已采集，**实际Excel打开/逐格UI一致性仍NT**。
- 后端独立构建成功；前端实际构建成功（约1分38秒，有chunk大小提示，无构建错误）。不把构建通过当验收通过。

## DEF-S3-081（高，TC-021.S1/SRS_F006.R05）

1. 配置管理员登录真实Edge页面`/devices/G6_UNTESTED_134145/capabilities`。
2. 编辑已启用G119_LIVE，名称改为GPT V120 UI edit，保存。
3. UI发送PUT，包括`capabilityCode`、`capabilityType`、`templateId`以及可编辑字段；返回HTTP500/code1000“系统繁忙，请稍后重试”，表单保持打开，修改未保存。
4. 后端原始异常：`Unrecognized field "capabilityCode" (class com.airport.ai.device.dto.UpdateDeviceCapabilityRequest)`；该DTO仅支持inputParams/capabilityName/applicableCondition/outputParams/capabilityDescription。

证据：`evidence/SRS_F006-V1.120-ui-edit-r3.json`（请求/响应/页面校验及提示），`...-capability-edit-ui-r3.png`。前端DeviceCapabilityView.handleSubmit展开完整form后直接PUT，API层也未过滤；与早期R01的同类UI编辑失败一致，本轮仍真实存在。不能用精简字段API更新成功代替UI通过。

Claude请按更新DTO白名单构造payload，保留编码/类型不可编辑约束；顺带核对模板编辑的同类契约，避免修复后紧接另一个同源失败。完成针对性UI契约/后端回归并递增唯一V1.N，推送产品/标签与READY_FOR_GPT；不改证据、不移动旧标签。

## 探针裁决与保留证据

- 首次计数探针误写capability_templates，改为实际capability_template；前4个P未重跑，错误记录保留batch.probeCorrections。
- UI探针最初按“确定”按钮名定位，但实际Modal使用默认英文按钮，等待超时且没有PUT请求，属于探针问题。原`...-ui.json`、`...-ui-edit-r2.json`及`...-capability-edit-diagnostic.png`保留；改用实际footer主按钮后才产生真实PUT500。F只依最终网络与后端异常判定，未将探针超时算F。
- V118版本历史/SQL和V119门禁P保留各自SHA，代码影响复核适用，未冒充V120重新执行；旧F/NT不删。本轮无基线内容变更。

## 剩余工作与环境

在用能力停用恢复/候选切换及无候选处理、超时分支、实际Excel打开/矩阵逐格核对、模板预填UI、全平台规划exists过滤、完整受影响邻接仍NT。已准备`.local-test/gpt-f006-v120-recovery.py`，**尚未执行，不宣称恢复通过**。因明确F及时交回，F006不推进F007。

GPT自有schema tip_gpt_f006_v118_20261030已V22；后端18129/Redis10，运行记录`.local-test/gpt-f006-v120-runtime.json`（PID3820需恢复时核对），模拟器18130，Vite15179（元数据`gpt-f006-v120-vite.json`）。18131只在新设备元数据预留，替代模拟器尚未启动。不要操作对方资源或重跑首次建库脚本。
