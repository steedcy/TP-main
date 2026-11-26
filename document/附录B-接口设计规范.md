# 附录B：接口设计规范

**文档版本**: V2.0
**编制日期**: 2026-09-04
**适用项目**: 智慧机场人工智能集群协同服务平台
**对齐基线**: 20260904-智慧机场人工智能集群协同服务平台-需求规格说明书-V1.4.md（7.2节接口需求）

**V2.0版本说明**：本版本为全量重写。V1.0版本围绕视频流、人脸识别、DeepSeek/Kimi商业API等内容编制，与V1.4正文的设备代理协同、开放式任务规划、监督智能体风险判定架构不符，故整篇替换。TBD-01~TBD-08已拍板结论见附录末尾对照表，本次接口字段设计已按拍板结论落地。

---

## 目录

1. [REST API设计规范](#1-rest-api设计规范)
2. [统一响应格式](#2-统一响应格式)
3. [错误码定义](#3-错误码定义)
4. [内部接口（7.2.1）](#4-内部接口)
5. [外部接口（7.2.2）](#5-外部接口)
6. [业务功能接口清单](#6-业务功能接口清单)
7. [WebSocket接口规范](#7-websocket接口规范)
8. [TBD拍板结论对照表](#8-tbd拍板结论对照表)

---

## 1. REST API设计规范

### 1.1 URL设计原则

**基本规则**：
- 使用小写字母和连字符（kebab-case）
- 使用名词复数形式表示资源集合
- 使用路径参数表示资源ID
- 使用查询参数表示过滤、排序、分页

**URL结构**：
```
https://{domain}/api/v1/{resource}/{id}?{query_params}
```

**示例**：
```
GET /api/v1/tasks?status=EXECUTING&page=1&size=20
GET /api/v1/tasks/{taskId}
POST /api/v1/tasks
POST /api/v1/tasks/{taskId}/terminate
```

### 1.2 HTTP方法语义

| 方法 | 用途 | 幂等性 | 示例 |
|---|---|---|---|
| GET | 查询资源 | 是 | GET /api/v1/tasks |
| POST | 创建资源或触发业务动作 | 否（业务动作类须配合指令编号实现幂等） | POST /api/v1/tasks |
| PUT | 完整更新资源 | 是 | PUT /api/v1/devices/{id} |
| PATCH | 部分更新资源 | 否 | PATCH /api/v1/capabilities/{id} |
| DELETE | 删除资源 | 是 | DELETE /api/v1/devices/{id} |

### 1.3 请求头规范

**必选请求头**：
```http
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json
```

**可选请求头**：
```http
X-Request-ID: {UUID}  # 请求追踪ID，下发类消息作为指令编号使用
Accept-Language: zh-CN
```

### 1.4 分页规范

**请求参数**：
```json
{
  "page": 1,
  "size": 20
}
```

**响应格式**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "content": [],
    "totalElements": 150,
    "totalPages": 8,
    "page": 1,
    "size": 20,
    "first": true,
    "last": false
  }
}
```

### 1.5 版本管理

**版本策略**：当前不做版本管理，保持向后兼容。未来如需版本管理，采用URL路径方式（/api/v2/）。

---

## 2. 统一响应格式

### 2.1 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": "2026-09-04T10:30:00Z"
}
```

### 2.2 失败响应

```json
{
  "code": 4101,
  "message": "任务不存在",
  "data": null,
  "timestamp": "2026-09-04T10:30:00Z",
  "path": "/api/v1/tasks/999",
  "method": "GET"
}
```

### 2.3 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| code | Integer | 是 | 业务状态码（见第3节错误码定义） |
| message | String | 是 | 提示信息（中文） |
| data | Object/Array | 否 | 业务数据，失败时为null |
| timestamp | String | 是 | 响应时间（ISO 8601格式） |
| path | String | 否 | 请求路径（仅错误响应） |
| method | String | 否 | 请求方法（仅错误响应） |

---

## 3. 错误码定义

### 3.1 错误码分类

| 错误码范围 | 分类 | 说明 |
|---|---|---|
| 200 | 成功 | 请求成功 |
| 1xxx | 系统错误 | 服务器内部错误 |
| 2xxx | 认证授权错误 | 用户身份验证失败 |
| 3xxx | 请求参数错误 | 客户端请求参数不合法 |
| 40xx | 账号管理错误 | 用户/角色相关业务错误 |
| 41xx | 任务规划与执行错误 | 任务全生命周期相关业务错误 |
| 42xx | 设备与代理错误 | 设备档案、设备代理相关业务错误 |
| 43xx | 能力管理错误 | 设备能力、能力边界相关业务错误 |
| 44xx | 基线模板错误 | 基线服务模板相关业务错误 |
| 45xx | 风险规则错误 | 确定性高风险规则配置相关业务错误 |
| 5xxx | 外部依赖错误 | 规划模型服务、设备接口调用失败 |

### 3.2 详细错误码清单

#### 系统错误 (1xxx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 1000 | 系统内部错误 | 500 | 未预期的服务器错误 |
| 1001 | 服务不可用 | 503 | 服务正在维护或重启 |
| 1002 | 数据库连接失败 | 500 | 数据库访问异常 |

#### 认证授权错误 (2xxx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 2000 | 未授权访问 | 401 | 缺少或无效的JWT Token |
| 2001 | Token已过期 | 401 | 会话空闲超过30分钟 |
| 2002 | 用户名或密码错误 | 401 | 登录凭证不正确，统一提示不区分原因 |
| 2003 | 无权限访问 | 403 | 用户角色无权限执行该操作 |
| 2004 | 账号已停用 | 403 | 账号status为INACTIVE，拒绝登录 |
| 2005 | 账号已锁定 | 403 | 账号status为LOCKED，需系统管理员解锁 |
| 2006 | 连续3次密码输入错误，账号已锁定 | 403 | 刚触发密码错误锁定，locked_reason记录本次原因 |

#### 请求参数错误 (3xxx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 3000 | 请求参数缺失 | 400 | 必填参数未提供 |
| 3001 | 参数格式错误 | 400 | 参数类型或格式不正确 |
| 3002 | 参数值超出范围 | 400 | 参数值不在允许范围内（如步骤超时超出10~600秒） |

#### 账号管理错误 (40xx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 4001 | 用户不存在 | 404 | 查询/操作的用户ID不存在 |
| 4002 | 用户名已被占用 | 409 | 创建账号时username重复 |
| 4003 | 用户未锁定，无需解锁 | 400 | 用户status不是LOCKED |
| 4004 | 不允许停用当前登录账号 | 400 | 系统管理员误操作自身账号 |

#### 任务规划与执行错误 (41xx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 4101 | 任务不存在 | 404 | 查询的任务编号不存在 |
| 4102 | 任务状态不允许操作 | 409 | 任务当前状态不支持该操作（如已完成任务不可终止） |
| 4103 | 结构校验不通过 | 400 | 步骤数超过5、存在循环、字段不完整 |
| 4104 | 能力校验不通过 | 400 | 能力缺口或无在线候选代理 |
| 4105 | 约束校验不通过 | 400 | 资源冲突、参数缺失或含运动安全指令 |
| 4106 | 计划包含运动安全控制字段 | 400 | 检出速度/加速度/姿态/路径点等字段，拦截并记录 |
| 4107 | 重新规划次数已达上限 | 409 | 单任务局部重新规划已使用1次 |
| 4108 | 无可用基线模板 | 404 | 高风险降级或规划失败时未匹配到已启用模板 |
| 4109 | 试图对未通过校验的计划执行监督判定 | 400 | 拦截并记录拦截事件 |
| 4110 | 试图对硬性校验失败的计划强行放行 | 400 | 拦截并记录拦截事件 |

#### 设备与代理错误 (42xx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 4201 | 设备不存在 | 404 | 查询/操作的设备编码不存在 |
| 4202 | 设备编码已存在 | 409 | 创建设备时编码重复 |
| 4203 | 设备连接测试未通过 | 400 | 未通过连接测试的设备不得创建启用代理 |
| 4204 | 设备代理不存在 | 404 | 查询的代理编号不存在 |
| 4205 | 设备已存在启用代理 | 409 | 一设备仅可对应一个启用代理 |
| 4206 | 设备存在进行中任务，不可删除 | 409 | — |
| 4207 | 设备离线 | 400 | 目标设备代理在线状态为离线，退出候选集合 |
| 4208 | 接入对象数量已达上限 | 409 | 超过8.1节TBD-01接入规模上限（演示10/系统20，可配置） |

#### 能力管理错误 (43xx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 4301 | 能力编码已存在 | 409 | 同设备内能力编码重复 |
| 4302 | 能力类型超出设备类型边界 | 400 | 按5.2.4A越界校验拒绝保存 |
| 4303 | 能力未通过模拟调用测试 | 400 | 未测试通过的能力不得启用 |
| 4304 | 能力已停用，不参与规划 | 400 | — |
| 4305 | 设备类型不支持任何能力类型 | 400 | 保存设备类型能力边界时校验，每类设备至少支持1个能力 |
| 4306 | 能力模板已被设备实例使用，不可删除 | 409 | 只能停用 |

#### 基线模板错误 (44xx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 4401 | 模板名称已存在 | 409 | — |
| 4402 | 模板未试运行或试运行未通过 | 400 | 仅试运行成功可启用 |
| 4403 | 模板步骤总数超过5 | 400 | — |
| 4404 | 预置任务族模板不可删除 | 400 | 超规行李处置/特殊旅客服务/航班变更应对 |
| 4405 | 模板版本已变更，需重新试运行 | 400 | — |

#### 风险规则错误 (45xx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 4501 | 规则编号已存在 | 409 | — |
| 4502 | 监督服务不可用或判定超时 | 503 | 任务转入待人工处理，不下发设备指令 |
| 4503 | 监督智能体输出无法确定 | 200 | 非错误，业务结果之一，任务转入待人工处理 |

#### 外部依赖错误 (5xxx)

| 错误码 | 错误信息 | HTTP状态码 | 说明 |
|---|---|---|---|
| 5001 | 规划模型服务调用失败 | 500 | 超时（单次60秒）或返回非0 resultCode |
| 5002 | 规划模型服务不可用 | 503 | 触发高风险基线降级流程（5.4.6） |
| 5003 | 设备接口调用超时 | 500 | 指令下发无响应，按5.5.2/5.5.3重试或恢复 |

---

## 4. 内部接口

对应V1.4正文7.2.1节，均为本项目定制开发，用于平台内部模块间协作，均须遵循三类校验与运动安全边界约束（详见5.2.5、5.4.4）。

### 4.1 设备代理统一消息接口

由设备接入模块提供给规划、执行监督模块调用，支持能力查询、状态查询、任务接受、任务拒绝、执行反馈、任务取消六类业务消息。每条下发类消息携带唯一指令编号（commandId），用于重试幂等与事件关联。消息不得承载运动安全控制字段，检出即拦截并记录（错误码4106）。

**接口**: `POST /internal/v1/device-agent/messages`

**通用请求字段**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| commandId | String | 是 | 指令编号，全局唯一；重试沿用同一编号 |
| messageType | String | 是 | CAPABILITY_QUERY / STATUS_QUERY / TASK_ACCEPT / TASK_REJECT / EXECUTION_FEEDBACK / TASK_CANCEL |
| agentId | String | 是 | 设备代理编号 |
| payload | Object | 否 | 按messageType变化，见下表 |

**payload结构（按messageType）**：

| messageType | payload字段 |
|---|---|
| CAPABILITY_QUERY | capabilityType（String，否，过滤条件） |
| STATUS_QUERY | 无 |
| TASK_ACCEPT（下发） | taskId、stepSeq、capabilityType、inputParams（Object） |
| TASK_ACCEPT（响应） | accepted（Boolean）、rejectReason（String，拒绝时必填） |
| TASK_REJECT | rejectReasonCode（String） |
| EXECUTION_FEEDBACK | executionResult（SUCCESS/FAILED/TIMEOUT）、reasonCode（String）、outputParams（Object） |
| TASK_CANCEL | taskId、stepSeq；语义为请求结束当前业务任务，非运动安全急停 |

**响应示例**（能力查询）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "commandId": "CMD-20260904-0001",
    "capabilities": [
      {"code": "CAP_ESCORT", "name": "陪同服务", "status": "ENABLED"}
    ]
  }
}
```

**校验拦截错误码**：4106（含运动安全控制字段：速度、加速度、姿态、路径点、避障、急停、限速、失联停靠）

---

### 4.2 规划上下文查询接口

由设备接入模块提供给规划模块调用，返回全部启用设备代理的能力、在线状态、位置、负载和可用时间，生成上下文快照标识（详见5.4.2）。

**接口**: `GET /internal/v1/planning/context-snapshot`

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "snapshotId": "CTX-20260904-0001",
    "generatedAt": "2026-09-04T10:30:00Z",
    "agents": [
      {
        "agentId": "AGT-0007",
        "capabilities": ["CAP_ESCORT", "CAP_NAVIGATION"],
        "onlineStatus": "ONLINE",
        "location": {"x": 120.5, "y": 88.2, "zone": "T2-B区"},
        "workload": "IDLE",
        "availableUntil": null
      }
    ],
    "capabilityCoverage": {"available": ["CAP_ESCORT"], "missing": []}
  }
}
```

**说明**：离线、停用、归档代理不纳入agents清单（5.4.2规则2）；快照生成后关联对应任务；上下文快照生成时间超过60秒（TBD-04拍板结论）视为"接近过期"风险信号，供5.4.5监督判定使用。

---

### 4.3 计划校验接口

由校验模块提供给规划模块和监督模块调用，执行结构、能力、约束三类校验，为硬性闸门，任何调用方不得绕过（详见5.4.4）。

**接口**: `POST /internal/v1/planning/plans/validate`

**请求**：
```json
{
  "planId": "PLAN-20260904-0001",
  "taskId": "TASK-20260904-0001",
  "snapshotId": "CTX-20260904-0001",
  "steps": [
    {
      "stepSeq": 1,
      "stepGoal": "机器人前往登机口迎接旅客",
      "capabilityType": "CAP_ESCORT",
      "inputParams": {"targetLocation": "GATE_A05", "escortMode": "LEAD", "maxDuration": 600},
      "precondition": "候选机器人在线且空闲",
      "completionCondition": "旅客到达登机口"
    }
  ]
}
```

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "structureCheck": "PASS",
    "capabilityCheck": "PASS",
    "constraintCheck": "FAIL",
    "errors": [
      {"errorType": "RESOURCE_CONFLICT", "description": "候选机器人备用数量不足", "stepSeq": 1, "reasonCode": "ERR_RESOURCE_CRITICAL"}
    ]
  }
}
```

**失败错误码**：4103（结构）、4104（能力）、4105（约束）、4106（运动安全字段）

---

### 4.4 监督判定接口

由监督智能体提供给规划模块调用，输入为已通过三类校验的冻结计划版本与规划上下文快照，输出风险等级、风险原因码、判定依据、置信度、推荐处置和所用规则集版本（详见5.4.5）。

**接口**: `POST /internal/v1/supervision/risk-assessment`

**请求**：
```json
{
  "planVersionId": "PLANV-0001",
  "snapshotId": "CTX-20260904-0001"
}
```

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "riskLevel": "HIGH",
    "riskReasonCode": "RULE_ESCORT_SPECIAL_PASSENGER",
    "judgmentBasis": "命中确定性高风险规则：移动机器人陪同对象为特殊旅客",
    "confidence": 0.92,
    "recommendedAction": "BASELINE_DOWNGRADE",
    "ruleSetVersion": "V1.2"
  }
}
```

**riskLevel取值**：LOW / HIGH / UNDETERMINED

**recommendedAction取值**：AUTO_EXECUTE / BASELINE_DOWNGRADE / MANUAL_HANDLING

**确定性高风险规则命中条件（TBD-03拍板结论，ruleSetVersion内维护）**：

| 规则编号 | 规则名称 | 命中条件 |
|---|---|---|
| RULE_ESCORT_SPECIAL_PASSENGER | 移动机器人会合或陪同 | 服务对象为特殊旅客（5.6.4场景）时命中；普通空间引导（5.2节场景）不命中 |
| RULE_CROSS_ZONE | 跨区域连续服务 | 仅移动服务机器人适用；同一任务链条中跨越预定义区域边界1次及以上命中 |
| RULE_RESOURCE_CRITICAL | 资源冲突临界状态 | 任务申请资源时可用备用候选设备数量低于配置阈值（默认1）命中 |

说明：航班/登机口公共信息发布已按拍板结论移出确定性高风险规则清单，改为可自主执行、不需人工确认。

**风险信号（辅助判定，两个及以上组合触发基线降级，TBD-04拍板结论）**：

| 信号 | 判定标准 |
|---|---|
| 模型低置信度 | confidence < 0.8 |
| 候选差异较大 | 不做平台层量化，采信规划模型输出的候选差异信号标签 |
| 上下文接近过期 | 快照生成时间距当前超过60秒 |

**异常错误码**：4109（对未通过校验计划判定）、4502（监督服务不可用/超时）

---

### 4.5 基线模板匹配接口

由基线模板模块提供给规划模块和监督模块调用，按任务族、所需能力和五步限制返回可匹配的已启用模板及其版本（详见5.4.6）。

**接口**: `GET /internal/v1/baseline-templates/match?taskFamily={taskFamily}&requiredCapabilities={list}&maxSteps=5`

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "matched": true,
    "templateId": "TPL-0003",
    "templateVersion": "V1.1",
    "matchBasis": "任务族精确匹配；步骤数3；最近试运行通过时间2026-09-01"
  }
}
```

**匹配优先级**：任务族精确匹配优先 > 步骤数少优先 > 最近试运行通过优先

**未匹配错误码**：4108（无可用基线模板）

---

### 4.6 任务事件写入接口

由过程追溯模块提供给全部业务模块调用，按任务编号写入事件；事件仅可追加，不可修改或删除（详见5.7.1）。

**接口**: `POST /internal/v1/tasks/{taskId}/events`

**请求**：
```json
{
  "eventType": "SUPERVISION_JUDGED",
  "occurredAt": "2026-09-04T10:31:05Z",
  "trigger": "SYSTEM",
  "reasonCode": "RULE_ESCORT_SPECIAL_PASSENGER",
  "detailSummary": "监督判定高风险，转基线降级"
}
```

**eventType枚举**（节选，覆盖5.7.1全部串联内容）：GOAL_SUBMITTED、GOAL_CLARIFIED、GOAL_UNDERSTANDING_FAILED、CONTEXT_SNAPSHOT_GENERATED、PLAN_GENERATED、PLAN_VALIDATED、SUPERVISION_JUDGED、BASELINE_DOWNGRADED、DEVICE_ASSIGNED、DEVICE_RESPONDED、EXECUTION_FEEDBACK_RECEIVED、REPLANNING_TRIGGERED、MANUAL_TERMINATED、TASK_COMPLETED、TASK_FAILED

**响应**：`{"code": 200, "message": "success", "data": {"eventId": "EVT-000123"}}`

---

### 4.7 设备类型能力边界查询接口（V1.3/V1.4新增）

由5.2.4A设备类型能力边界模块提供给5.2.4设备能力画像管理模块调用，返回指定设备类型支持的能力类型清单及对应标准能力模板；供设备实例创建能力时进行越界校验（详见5.2.4A、5.2.4）。

**接口**: `GET /internal/v1/device-types/{deviceTypeCode}/capability-boundary`

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "deviceTypeCode": "MOBILE_ROBOT",
    "deviceTypeName": "移动服务机器人",
    "supportedCapabilityTypes": ["CAP_NAVIGATION", "CAP_ESCORT", "CAP_NOTIFICATION", "CAP_INFO_DISPLAY"],
    "templates": [
      {"templateCode": "TPL_ESCORT_STD", "capabilityType": "CAP_ESCORT", "templateVersion": "V1.0", "templateStatus": "ACTIVE"}
    ]
  }
}
```

**越界拒绝错误码**：4302

---

## 5. 外部接口

对应V1.4正文7.2.2节。

### 5.1 目标理解服务调用接口（本系统调用外部系统，V1.4新增）

对应5.4.1开放式任务目标提交与理解。**方案A（已确认）**：目标理解与5.1A候选计划生成是外部规划模型服务的两个独立端点，而非同一次调用——业务规则4要求"信息补充完成前不得进入计划生成"，若两者合一，理解阶段将不可避免地先触发一次规划调用，无法在该卡点真正拦截信息不全的任务；本接口因此单独定义契约，不复用candidate/generate接口的请求响应结构，但共用同一模型服务地址、鉴权方式与60秒超时约束（app.planning-model.*配置）。

| 项目 | 内容 |
|---|---|
| 接口类型 | HTTPS受控调用 |
| 调用频次 | 任务提交、每次补充信息后各触发一次 |
| 超时 | 单次请求60秒，超时或异常均不进入计划生成，不下发任何设备指令 |
| 其它 | 与5.1A共用模型服务地址和鉴权配置；请求路径固定追加`/v1/goal/understand`后缀区分端点 |

**接口**: `POST {模型服务地址}/v1/goal/understand`

**请求体**：
```json
{
  "requestId": "REQ-20260904-0002",
  "taskGoal": "协助行动不便旅客前往A05登机口",
  "taskFamily": "SPECIAL_PASSENGER_SERVICE",
  "sceneParams": {"assistanceType": "MOBILITY_IMPAIRED"},
  "clarificationAnswers": [
    {"answers": {"目的地是哪个登机口？": "A05"}}
  ]
}
```

**响应体**：
```json
{
  "resultCode": "0",
  "errorMessage": null,
  "origin": "T2-CHECKIN",
  "destination": "GATE_A05",
  "constraints": ["不得下发运动安全控制指令"],
  "completionCondition": "旅客到达登机口",
  "infoComplete": true,
  "missingInfoQuestions": [],
  "unrelatedToAnyFamily": false,
  "inferredTaskFamily": "SPECIAL_PASSENGER_SERVICE"
}
```

**输入参数说明**：

| 参数名称 | 参数类型 | 是否必填 | 参数说明 |
|---|---|---|---|
| requestId | 字符 | 是 | 请求唯一标识，用于超时与重试关联 |
| taskGoal | 字符 | 是 | 原始任务目标原文，须原文保存不得改写（对应5.4.1业务规则5） |
| taskFamily | 字符 | 否 | 运行操作员指定的任务族；为空时由响应inferredTaskFamily承载系统判定结果 |
| sceneParams | 对象 | 否 | 场景参数，不得包含旅客真实身份信息（对应5.4.1业务规则6） |
| clarificationAnswers | 数组 | 否 | 首次提交为空；补充信息后携带运行操作员对missingInfoQuestions的逐条回答 |

**输出参数说明**：

| 参数名称 | 参数类型 | 参数说明 |
|---|---|---|
| resultCode | 字符 | 0：成功；非0：失败 |
| errorMessage | 字符 | 错误描述，失败时必填 |
| origin/destination/constraints/completionCondition | 字符/数组 | 提取出的起点、目的地、约束条件、完成条件（对应业务规则2） |
| infoComplete | 布尔 | 关键信息是否完整；为false时missingInfoQuestions不得为空 |
| missingInfoQuestions | 数组 | 待补充问题清单，逐条展示于5.4.1界面元素"待补充问题" |
| unrelatedToAnyFamily | 布尔 | true表示目标内容与已定义任务族及能力类型完全无关（对应异常路径4c） |
| inferredTaskFamily | 字符 | 系统按目标内容判定出的任务族，仅在运行操作员未指定时使用 |

**错误码**（resultCode非0时，与5.1A规划模型服务共用编号）：1001输入参数校验失败；1002模型服务内部错误；1003模型服务超时（60秒）；1004模型服务不可用。

**服务不可用/超时处理**：任务停留在PLANNING，不进入计划生成，提示运行操作员稍后重试；对应本文档错误码4113。

---

### 5.1A 候选计划生成服务调用接口（本系统调用外部系统）

| 项目 | 内容 |
|---|---|
| 接口类型 | HTTPS受控调用 |
| 调用频次 | 按规划请求触发，受并发任务不超过10个约束 |
| 超时 | 单次请求60秒 |
| 其它 | 模型可替换，支持外部模型服务或本地模型；模拟模型仅用于接口自测，不作为验收基线 |

**接口**: `POST {模型服务地址}/v1/planning/generate`

**请求体**：
```json
{
  "requestId": "REQ-20260904-0001",
  "taskGoal": "协助行动不便旅客前往A05登机口",
  "taskFamily": "SPECIAL_PASSENGER_SERVICE",
  "sceneParams": {"assistanceType": "MOBILITY_IMPAIRED", "origin": "T2-CHECKIN", "destination": "GATE_A05"},
  "constraints": ["不得下发运动安全控制指令", "步骤数不超过5"],
  "capabilityContext": [
    {"capabilityType": "CAP_ESCORT", "candidateCount": 2, "zone": "T2-B区", "availableUntil": null}
  ],
  "remainingStepQuota": 5,
  "completedSteps": []
}
```

**响应体**：
```json
{
  "resultCode": "0",
  "errorMessage": null,
  "planSteps": [
    {
      "stepSeq": 1,
      "stepGoal": "机器人前往起点接引旅客",
      "capabilityType": "CAP_ESCORT",
      "inputParams": {"targetLocation": "T2-CHECKIN", "escortMode": "LEAD", "maxDuration": 600},
      "precondition": "候选机器人在线且空闲",
      "completionCondition": "机器人到达起点",
      "failureHandling": "重试一次或切换候选机器人"
    }
  ],
  "planRationale": "根据旅客协助类型选取陪同服务能力，路径最短原则选择起点最近的空闲机器人",
  "confidence": 0.92
}
```

**输入参数说明**：

| 参数名称 | 参数类型 | 是否必填 | 参数说明 |
|---|---|---|---|
| requestId | 字符 | 是 | 请求唯一标识，用于超时与重试关联 |
| taskGoal | 字符 | 是 | 脱敏后的自然语言任务目标原文 |
| taskFamily | 字符 | 是 | 任务族标识 |
| sceneParams | 对象 | 否 | 场景参数，已脱敏 |
| constraints | 数组 | 是 | 任务族约束与完成条件 |
| capabilityContext | 数组 | 是 | 可用能力上下文，每项含能力类型、候选代理数、区域、可用时间 |
| remainingStepQuota | 整数 | 是 | 剩余可执行步骤额度，取值1~5 |
| completedSteps | 数组 | 否 | 局部重新规划时携带的已完成步骤及其结果 |

**输出参数说明**：

| 参数名称 | 参数类型 | 参数说明 |
|---|---|---|
| resultCode | 字符 | 0：成功；非0：失败 |
| errorMessage | 字符 | 错误描述，失败时必填 |
| planSteps | 数组 | 候选计划步骤列表 |
| planRationale | 字符 | 规划说明，作为规划依据展示 |
| confidence | 数值 | 模型置信度，作为监督判定的风险信号之一（<0.8视为低置信度，TBD-04拍板结论），不得覆盖三类校验结果 |

**错误码**（resultCode非0时）：

| resultCode | 说明 |
|---|---|
| 1001 | 输入参数校验失败 |
| 1002 | 模型服务内部错误 |
| 1003 | 模型服务超时（60秒） |
| 1004 | 模型服务不可用 |

**服务不可用/超时处理**：转入5.4.6高风险基线降级流程，对应本文档5xxx错误码5001/5002。

---

### 5.2 平台统一设备接口（本系统提供给设备调用 / 调用设备）

| 项目 | 内容 |
|---|---|
| 接口类型 | 平台统一设备接口，首期以模拟适配器实现 |
| 调用方向 | 设备上报状态与执行反馈（设备调用平台）；平台下发业务指令与任务取消（平台调用设备） |
| 获取频率 | 状态按15秒周期上报（默认，可配置5~60秒）；测量、变更、执行反馈等事件实时上报；发布与引导指令按需下发 |
| 其它 | 首期以模拟接口为验收基线；平台仅下发业务意图，不下发运动安全控制指令 |

**设备上报接口**：`POST /device-api/v1/agents/{agentId}/report`

**请求体**（状态上报）：
```json
{
  "onlineStatus": "ONLINE",
  "workStatus": "IDLE",
  "location": {"x": 120.5, "y": 88.2, "zone": "T2-B区"},
  "reportedAt": "2026-09-04T10:30:00Z"
}
```

**请求体**（执行反馈）：
```json
{
  "commandId": "CMD-20260904-0001",
  "executionResult": "SUCCESS",
  "reasonCode": null,
  "outputParams": {"arrivalStatus": "ARRIVED", "actualDistance": 85.2, "actualDuration": 420}
}
```

**平台下发接口**：`POST /device-api/v1/agents/{agentId}/commands`

**请求体**：
```json
{
  "commandId": "CMD-20260904-0002",
  "taskId": "TASK-20260904-0001",
  "stepSeq": 1,
  "capabilityType": "CAP_ESCORT",
  "inputParams": {"targetLocation": "GATE_A05", "escortMode": "LEAD", "maxDuration": 600}
}
```

**格式非法处理**：丢弃该次上报并记录格式异常事件（错误码3001）。

**心跳超时处理**：默认30秒（可配置10~120秒）未收到上报标记离线，退出候选集合，生成离线异常事件（错误码4207）。

---

## 6. 业务功能接口清单

本节补充V1.4正文7.2节未列出、但正文功能需求（第五章）实际依赖的前端对接接口，按业务模块分组。

### 6.1 用户认证模块（对应5.1.1 + 用户登录密码锁定功能补充）

#### 6.1.1 用户登录

**接口**: `POST /api/v1/auth/login`

**请求体**：
```json
{"username": "admin", "password": "password123"}
```

**成功响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "tokenType": "Bearer",
    "expiresIn": 1800,
    "user": {"id": 1, "username": "admin", "realName": "系统管理员张三", "role": "SYSTEM_ADMIN"}
  }
}
```

**密码错误未锁定响应**（code=2002）：
```json
{"code": 2002, "message": "账号或密码错误", "data": {"remainingAttempts": 1}}
```

**账号已锁定响应**（code=2005）：
```json
{"code": 2005, "message": "账号或密码错误", "data": null}
```

说明：账号或密码错误的提示统一为"账号或密码错误"，不区分账号不存在、密码错误、账号停用、账号锁定（5.1.1业务规则3、4）。remainingAttempts等锁定相关细节仅供前端节流展示，不改变统一提示文案。

#### 6.1.2 用户登出

**接口**: `POST /api/v1/auth/logout`

**请求头**: `Authorization: Bearer {token}`

**成功响应**: `{"code": 200, "message": "登出成功"}`

#### 6.1.3 解锁账号（仅系统管理员）

**接口**: `POST /api/v1/users/{userId}/unlock`

**成功响应**：
```json
{"code": 200, "message": "success", "data": {"userId": 1, "username": "opuser01", "status": "ACTIVE", "unlockedAt": "2026-09-04T10:30:00Z", "unlockedBy": "admin"}}
```

**错误码**：4003（用户未锁定，无需解锁）

---

### 6.2 账号管理模块（对应5.1.1，字段范围按TBD-06拍板结论）

#### 6.2.1 创建账号

**接口**: `POST /api/v1/users`

**请求体**：
```json
{
  "username": "opuser01",
  "password": "Init@12345",
  "realName": "李四",
  "role": "OPERATOR",
  "contact": "13800000000"
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| username | String | 是 | 1~32位，系统内唯一 |
| password | String | 是 | 8~32位，服务端加盐摘要存储 |
| realName | String | 是 | 1~32位 |
| role | Enum | 是 | SYSTEM_ADMIN（系统管理员）/ OPERATOR（运行操作员）/ CONFIG_ADMIN（配置管理员） |
| contact | String | 是 | 手机号或邮箱，用于密码重置通知 |
| status | Enum | — | 默认ACTIVE，创建时不可指定LOCKED |

**成功响应**：
```json
{"code": 200, "message": "success", "data": {"id": 12, "username": "opuser01", "createdAt": "2026-09-04T10:30:00Z"}}
```

**错误码**：4002（用户名已被占用）

#### 6.2.2 查询账号列表

**接口**: `GET /api/v1/users?role={role}&status={status}&page={page}&size={size}`

**响应data.content每项**：
```json
{
  "id": 12, "username": "opuser01", "realName": "李四", "role": "OPERATOR",
  "status": "ACTIVE", "contact": "13800000000",
  "failedLoginAttempts": 0, "lockedAt": null, "lockedReason": null,
  "lastLoginAt": "2026-09-04T09:00:00Z", "createdAt": "2026-09-01T10:00:00Z"
}
```

#### 6.2.3 重置密码 / 停用启用账号

**接口**: `POST /api/v1/users/{userId}/reset-password`

**请求体**: `{"newPassword": "New@12345"}`

**接口**: `POST /api/v1/users/{userId}/status`

**请求体**: `{"status": "INACTIVE"}`

**错误码**：4004（不允许停用当前登录账号）

---

### 6.3 设备档案与设备代理模块（对应5.2.1~5.2.3）

#### 6.3.1 创建设备档案

**接口**: `POST /api/v1/devices`

**请求体**：
```json
{
  "deviceCode": "ROBOT-001",
  "deviceName": "移动服务机器人01",
  "deviceType": "MOBILE_ROBOT",
  "isSimulated": true,
  "simulatedDeviceType": "MOBILE_ROBOT",
  "zone": "T2-B区",
  "location": {"x": 120.5, "y": 88.2},
  "accessParams": {"endpoint": "https://sim-adapter/robot-001", "credentialRef": "CRED-0012"},
  "reportInterval": 15,
  "remark": ""
}
```

**字段约束**：deviceCode 1~32位系统内唯一；deviceName 1~64位；deviceType枚举{SMART_DISPLAY, BAGGAGE_SCANNER, FLIGHT_DELAY_BOARD, MOBILE_ROBOT, SIMULATOR}；reportInterval默认15秒，范围5~60秒；accessParams.credentialRef不回显凭据原值；remark 0~200位。

**错误码**：4202（设备编码已存在）、4208（接入对象数量已达上限，TBD-01拍板结论：演示≤10/系统≤20，可配置）

#### 6.3.2 设备连接测试

**接口**: `POST /api/v1/devices/{deviceCode}/connection-test`

**响应**: `{"code": 200, "message": "success", "data": {"result": "PASS", "failReason": null}}`

#### 6.3.3 创建/查询设备代理

**接口**: `POST /api/v1/device-agents`（请求体：`{"deviceCode": "ROBOT-001"}`，前置要求连接测试通过，错误码4203）

**接口**: `GET /api/v1/device-agents/{agentId}`

**响应**：
```json
{
  "code": 200, "message": "success",
  "data": {
    "agentId": "AGT-0007", "deviceCode": "ROBOT-001", "deviceName": "移动服务机器人01",
    "agentStatus": "ENABLED", "onlineStatus": "ONLINE", "workStatus": "IDLE",
    "currentTask": null, "capabilities": ["CAP_ESCORT", "CAP_NAVIGATION"],
    "lastReportedAt": "2026-09-04T10:30:00Z"
  }
}
```

**停用代理**: `POST /api/v1/device-agents/{agentId}/disable`（需二次确认标记 `{"confirmed": true}`，错误码4205用于重复启用校验）

---

### 6.4 设备类型能力边界管理模块（对应5.2.4A）

#### 6.4.1 查询/维护设备类型能力边界

**接口**: `GET /api/v1/device-types/{deviceTypeCode}/capability-boundary`（响应结构同4.7节）

**接口**: `PUT /api/v1/device-types/{deviceTypeCode}/capability-boundary`

**请求体**：
```json
{
  "supportedCapabilityTypes": ["CAP_NAVIGATION", "CAP_ESCORT", "CAP_NOTIFICATION"],
  "typeDescription": "移动服务机器人可在航站楼内移动执行引导陪同任务",
  "constraintRules": "不得下发运动安全控制指令",
  "typicalScenarios": "旅客引导、特殊旅客陪同"
}
```

**错误码**：4305（设备类型不支持任何能力类型）

#### 6.4.2 能力模板管理

**接口**: `POST /api/v1/device-types/{deviceTypeCode}/capability-templates`

**请求体**：
```json
{
  "templateCode": "TPL_ESCORT_STD",
  "templateName": "标准陪同模板",
  "capabilityType": "CAP_ESCORT",
  "inputParams": [{"name": "targetLocation", "type": "String", "required": true}],
  "outputParams": [{"name": "arrivalStatus", "type": "String"}],
  "templateDescription": ""
}
```

**错误码**：4302（能力类型超出设备类型边界）、4306（已被使用不可删除，仅可停用）

---

### 6.5 设备能力画像管理模块（对应5.2.4）

**接口**: `POST /api/v1/devices/{deviceCode}/capabilities`

**请求体**：
```json
{
  "capabilityCode": "CAP-001",
  "capabilityName": "机器人陪同能力",
  "capabilityType": "CAP_ESCORT",
  "inputParams": [{"name": "escortMode", "type": "String", "required": true, "range": "LEAD/FOLLOW"}],
  "outputParams": [{"name": "arrivalStatus", "type": "String"}],
  "applicableCondition": "机器人处于空闲状态"
}
```

**能力测试**: `POST /api/v1/devices/{deviceCode}/capabilities/{capabilityCode}/test`（模拟调用测试，通过后可启用）

**能力启用/停用**: `POST /api/v1/devices/{deviceCode}/capabilities/{capabilityCode}/status`（`{"status": "ENABLED"}`）

**错误码**：4301（能力编码已存在）、4302（越界）、4303（未测试通过不可启用）

---

### 6.6 基线服务模板模块（对应5.3.1、5.3.2）

**创建模板**: `POST /api/v1/baseline-templates`

**请求体**：
```json
{
  "templateName": "特殊旅客服务标准模板",
  "templateIntent": "SPECIAL_PASSENGER_SERVICE",
  "inputParams": [{"name": "assistanceType", "type": "String", "required": true}],
  "steps": [
    {
      "stepSeq": 1,
      "capabilityType": "CAP_ESCORT",
      "paramMapping": [{"target": "targetLocation", "source": "TEMPLATE_INPUT.origin"}],
      "stepTimeout": 60,
      "completionCondition": "机器人到达起点"
    }
  ]
}
```

**字段约束**：templateIntent枚举{OVERSIZE_BAGGAGE_HANDLING, SPECIAL_PASSENGER_SERVICE, FLIGHT_CHANGE_RESPONSE, EXTENDED}；steps总数≤5，仅顺序执行；stepTimeout默认60秒，范围10~600秒（TBD-07拍板结论）。

**错误码**：4401（名称已存在）、4403（步骤总数超过5）

**试运行**: `POST /api/v1/baseline-templates/{templateId}/dry-run`

**请求体**: `{"inputParams": {"assistanceType": "MOBILITY_IMPAIRED"}, "simulatedDevices": [{"stepSeq": 1, "agentId": "AGT-0007"}]}`

**响应**：
```json
{
  "code": 200, "message": "success",
  "data": {"result": "SUCCESS", "stepResults": [{"stepSeq": 1, "result": "SUCCESS", "duration": 45}], "events": []}
}
```

**启用模板**: `POST /api/v1/baseline-templates/{templateId}/enable`（错误码4402：未试运行或未通过不可启用）

**删除模板**: `DELETE /api/v1/baseline-templates/{templateId}`（错误码4404：预置任务族模板不可删除）

---

### 6.7 任务规划与执行模块（对应5.4.1~5.5.6）

#### 6.7.1 提交任务目标

**接口**: `POST /api/v1/tasks`

**请求体**：
```json
{
  "taskGoal": "协助行动不便旅客前往A05登机口",
  "taskFamily": "SPECIAL_PASSENGER_SERVICE",
  "sceneParams": {"assistanceType": "MOBILITY_IMPAIRED", "origin": "T2-CHECKIN", "destination": "GATE_A05"}
}
```

**成功响应**：`{"code": 200, "message": "success", "data": {"taskId": "TASK-20260904-0001", "status": "PLANNING"}}`

**任务状态机全部状态（9种，5.5节）**：PLANNING（待规划）→ SUPERVISING（监督判定中）→ PENDING_ASSIGNMENT（待分配）/ DOWNGRADING（降级执行中）→ EXECUTING（执行中）→ COMPLETED（已完成）/ FAILED（失败）/ PENDING_MANUAL（待人工处理）/ MANUAL_TERMINATED（人工终止）

#### 6.7.2 查询任务列表/详情

**接口**: `GET /api/v1/tasks?status={status}&taskFamily={taskFamily}&page={page}&size={size}`

**接口**: `GET /api/v1/tasks/{taskId}`

**响应data结构**：taskId、status、taskFamily、taskGoal、goalParsingResult（origin/destination/constraints/completionCondition）、planVersionId、planSource（AUTONOMOUS/BASELINE_TEMPLATE）、supervisionResult（riskLevel/riskReasonCode/judgmentBasis/confidence）、downgradeInfo（downgradeReason/originalPlanVersion/baselineTemplateVersion，仅降级任务）、deviceAssignments、replanningReason、eventTimeline（数组，事件类型/时间/指令编号/原因码/操作人）

**待人工处理任务的处置操作**：`POST /api/v1/tasks/{taskId}/manual-actions`（`{"action": "FORCE_BASELINE" / "RETRY_PLANNING" / "MARK_FAILED" / "TERMINATE"}`）

#### 6.7.3 人工终止任务

**接口**: `POST /api/v1/tasks/{taskId}/terminate`

**请求体**：
```json
{"reason": "旅客取消服务需求", "confirmed": true}
```

**字段约束**：reason 1~200位必填；confirmed必须为true（对应5.5.6二次确认）

**说明**：人工终止为业务终止，语义等同于向设备下发TASK_CANCEL消息，不等同于设备安全急停（5.5.6其他说明）。

**成功响应**：
```json
{"code": 200, "message": "success", "data": {"taskId": "TASK-20260904-0001", "status": "MANUAL_TERMINATED", "deviceResults": [{"agentId": "AGT-0007", "result": "ACK"}]}}
```

---

### 6.8 旅客服务任务定义管理（对应5.6.1）

**接口**: `POST /api/v1/task-definitions`

**请求体**：
```json
{
  "taskName": "特殊旅客陪同服务",
  "goalTemplate": "协助{assistanceType}旅客从{origin}前往{destination}",
  "sceneParamDefinitions": [{"name": "assistanceType", "type": "String", "required": true, "description": "轮椅协助/无陪儿童/行动不便协助"}],
  "availableCapabilityTypes": ["CAP_ESCORT", "CAP_NAVIGATION", "CAP_INFO_DISPLAY"],
  "constraint": "不得下发运动安全控制指令",
  "expectedCompletionCondition": "旅客到达目的地"
}
```

**taskFamily标识**：预置任务族（OVERSIZE_BAGGAGE_HANDLING、SPECIAL_PASSENGER_SERVICE、FLIGHT_CHANGE_RESPONSE）不可删除；扩展任务族可增删。

**各场景任务输入参数（供taskGoal/sceneParams填充参考）**：

| 场景 | 输入字段 | 类型 | 必填 | 约束 |
|---|---|---|---|---|
| 超规行李处置（5.6.3） | baggageLocation | Enum | 是 | 预置行李处置点 |
| | targetCounter | Enum | 否 | — |
| 特殊旅客服务（5.6.4） | assistanceType | Enum | 是 | 轮椅协助/无陪儿童/行动不便协助等，不保存身份信息 |
| | origin / destination | Enum | 是 | 预置区域 |
| 航班变更应对（5.6.5） | flightNumber | String | 是 | 2~10位，虚构/脱敏 |
| | changeType | Enum | 是 | DELAY/GATE_CHANGE/CANCEL |
| | originalTime | Datetime | 是 | — |
| | newTime | Datetime | 条件必填 | 登机口变更/取消时可空 |
| | originalGate / newGate | Enum | 条件必填 | 登机口变更时newGate必填 |
| | changeDescription | String | 是 | 1~200位 |

---

### 6.9 任务过程追溯与操作记录（对应5.7.1、5.7.2）

**查询任务事件时间线**: `GET /api/v1/tasks/{taskId}/events`（响应结构同4.6节eventType枚举）

**查询计划版本列表**: `GET /api/v1/tasks/{taskId}/plan-versions`

**响应data每项**: `{"versionId": "PLANV-0001", "source": "AUTONOMOUS", "frozenAt": "2026-09-04T10:30:00Z", "executableStepCount": 3}`

**查询操作记录**: `GET /api/v1/operation-logs?operator={operator}&operationType={type}&from={from}&to={to}&page={page}&size={size}`

**响应data.content每项**：
```json
{
  "operatedAt": "2026-09-04T10:30:00Z", "operator": "admin", "role": "SYSTEM_ADMIN",
  "operationType": "DEVICE_CONFIG", "target": "ROBOT-001", "result": "SUCCESS",
  "sourceIp": "10.0.0.5", "detail": {"before": {"reportInterval": 15}, "after": {"reportInterval": 30}}
}
```

**operationType枚举**：LOGIN、LOGOUT、DEVICE_CONFIG、CAPABILITY_ENABLE_DISABLE、TEMPLATE_ENABLE_DISABLE、TASK_DEFINITION_CHANGE、RISK_RULE_CHANGE、MANUAL_TERMINATE、MANUAL_HANDLING

说明：detail中凭据字段（如accessParams.credentialRef）掩码展示，不还原原值。

---

### 6.10 二维态势展示（对应5.6.2，态势刷新周期TBD-02拍板结论）

**接口**: `GET /api/v1/situation/snapshot`

**响应**：
```json
{
  "code": 200, "message": "success",
  "data": {
    "generatedAt": "2026-09-04T10:30:00Z",
    "refreshIntervalSeconds": 5,
    "agents": [{"agentId": "AGT-0007", "deviceCode": "SIM-0001", "deviceName": "仿真航显", "deviceTypeCode": "SIMULATOR", "simulatedDeviceType": "SMART_DISPLAY", "location": {"x": 120.5, "y": 88.2, "zone": "T2-B区"}, "onlineStatus": "ONLINE", "workStatus": "BUSY", "currentTaskId": "TASK-20260904-0001"}]
  }
}
```

**说明**：刷新周期默认5秒、可配置、上限不超过15秒；验收以15秒为底线（TBD-02）。P4采用5秒轮询。WebSocket通道在服务端实现后可替代轮询；客户端不得假定未实现的推送端点可用。

---

### 6.11 确定性高风险规则配置（对应5.4.5配置界面）

**接口**: `POST /api/v1/risk-rules`

**请求体**：
```json
{
  "ruleCode": "RULE_ESCORT_SPECIAL_PASSENGER",
  "ruleContent": "移动机器人会合或陪同服务对象为特殊旅客时判定为高风险",
  "enabled": true
}
```

**接口**: `GET /api/v1/risk-rules?enabled={enabled}`

**响应data每项**: `{"ruleCode": "RULE_ESCORT_SPECIAL_PASSENGER", "ruleContent": "...", "ruleVersion": "V1.2", "enabled": true}`

**说明**：规则修改后系统自动生成新版本号（ruleVersion），由配置管理员维护（5.4.5业务规则5、10）。

**错误码**：4501（规则编号已存在）

---

### 6.12 仿真控制与设备执行追溯（P4）

下列管理接口仅配置管理员可调用，均使用用户JWT；平台再以对应设备的独立Bearer令牌调用仿真体控制接口。设备令牌不返回浏览器。

| 方法 | 接口 | 说明 |
|---|---|---|
| GET | `/api/v1/simulators` | 查询仿真类型、代理/在线/工作状态、最新位置、场景和最后上报时间。 |
| POST | `/api/v1/simulators/{deviceCode}/online` | 请求体`{"onlineStatus":"ONLINE|OFFLINE"}`，要求设备已绑定代理。ONLINE启动仿真实例逻辑运行状态并恢复心跳；OFFLINE停止逻辑运行、上报离线状态并暂停心跳。停止期间拒绝新承接/执行命令，仍允许取消命令。仿真进程本身保持运行以接收管理控制；进程启动/重启由部署环境负责。 |
| POST | `/api/v1/simulators/{deviceCode}/scenario` | 请求体`{"scenarioResult":"SUCCESS|FAILED|TIMEOUT|NO_OBJECT|LOST_TARGET"}`；特定类型只允许适用的结果。 |
| GET | `/api/v1/simulators/{deviceCode}/events` | 返回最近100条只追加设备事件。 |
| GET | `/api/v1/simulators/{deviceCode}/commands` | 返回最近100条命令摘要；不返回原始命令参数或设备令牌。 |

控制动作写入设备事件和操作记录。连接失败返回设备接口错误，不将管理请求伪装成成功。`NO_OBJECT`只用于行李测量，`LOST_TARGET`只用于移动机器人陪同。

---

## 7. WebSocket接口规范

### 7.1 连接建立

**WebSocket URL**: `wss://{domain}/ws/situation`

**连接握手**：
```
GET /ws/situation HTTP/1.1
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: {random_key}
Authorization: Bearer {JWT_TOKEN}
```

### 7.2 消息格式

**服务端推送消息**：
```json
{
  "type": "TASK_STATUS",
  "timestamp": "2026-09-04T10:30:00Z",
  "data": {"taskId": "TASK-20260904-0001", "status": "EXECUTING", "stepProgress": "1/3"}
}
```

**消息类型**：
- `TASK_STATUS`：任务状态更新（对应5.5.2步骤进度、5.5.5任务详情）
- `AGENT_STATUS`：设备代理在线/工作状态变化（对应5.2.3、5.6.2态势展示）
- `EXCEPTION_ALERT`：异常事件推送（对应5.5.3异常识别，异常类型：AGENT_OFFLINE/CAPABILITY_GAP/EXECUTION_TIMEOUT/STEP_FAILED/REPLANNING_FAILED）
- `MANUAL_PENDING_ALERT`：任务进入待人工处理提醒

### 7.3 心跳机制

**客户端**：每30秒发送一次ping帧

**服务端**：收到ping后立即回复pong帧

**超时断开**：连接空闲30分钟自动断开（与5.1.1会话空闲策略一致）

---

## 8. TBD拍板结论对照表

以下结论已于设计评审中拍板，供接口字段设计对照使用；正式定稿后需同步更新V1.4正文8.1节。

| 编号 | 拍板结论 | 已落地接口 |
|---|---|---|
| TBD-01 | 首期演示配置不超过10个，系统性能设计上限20个，接入上限做为可配置参数 | 6.3.1（错误码4208） |
| TBD-02 | 刷新周期可配置、默认5秒、上限不超过15秒，验收以15秒为底线 | 6.10 |
| TBD-03 | 四类高风险规则中航班/登机口公共信息发布移出高风险清单改为自主执行；机器人会合陪同限特殊旅客；跨区域连续服务限移动机器人+跨1次及以上；资源冲突临界状态按备用候选数量低于阈值判定 | 4.4 |
| TBD-04 | 模型低置信度阈值<0.8；候选差异较大不做平台层量化，采信模型输出信号；上下文接近过期阈值60秒 | 4.4、5.1 |
| TBD-05 | 规划模型服务详细契约（本附录5.1节已按V1.4正文原则补全字段级请求/响应示例与错误码，OpenAPI 3.1/JSON Schema正式文件另行发布） | 5.1 |
| TBD-06 | 账号管理字段范围：用户名、密码、角色、启用状态、姓名、联系方式、创建时间、最后登录时间 | 6.2 |
| TBD-07 | 步骤超时默认60秒，可配置范围10~600秒 | 6.6 |
| TBD-08 | 首期不做自动清理，保留全部演示期数据 | 6.9（不涉及清理接口） |

---

**文档结束**

**相关文档**：
- [附录A: 技术架构规范](./附录A-技术架构规范.md)
- [附录C: 性能指标详表](./附录C-性能指标详表.md)
- [附录D: 运维监控方案](./附录D-运维监控方案.md)
- [附录E: 测试验收标准](./附录E-测试验收标准.md)
- [数据库设计说明书](./数据库设计说明书.md)










