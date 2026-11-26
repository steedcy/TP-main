# 附录F：五类设备能力边界清单

**文档版本**: V1.0  
**编制日期**: 2026-09-03  
**适用项目**: 面向智慧机场的人工智能集群协同服务平台

---

## 目录

1. [设备类型概述](#1-设备类型概述)
2. [能力类型定义](#2-能力类型定义)
3. [五类设备能力边界](#3-五类设备能力边界)
4. [能力约束规则](#4-能力约束规则)
5. [能力模板库](#5-能力模板库)
6. [仿真体能力继承规则](#6-仿真体能力继承规则)

---

## 1. 设备类型概述

### 1.1 五类设备定义

本平台接入五类设备，每类设备具有明确的能力边界，用于任务规划时的能力匹配与校验。

| 设备类型 | 英文编码 | 主要用途 | 部署位置 |
|---|---|---|---|
| 智慧航显 | SMART_DISPLAY | 综合信息展示、旅客引导信息发布 | 航站楼各区域固定点位 |
| 智能行李测量设备 | BAGGAGE_SCANNER | 行李尺寸重量测量、超规检测 | 值机柜台、安检入口 |
| 航延屏 | FLIGHT_DELAY_BOARD | 航班延误信息发布 | 候机区、登机口 |
| 移动服务机器人 | MOBILE_ROBOT | 旅客引导、陪同服务、物品运送 | 航站楼内移动 |
| 仿真体 | SIMULATOR | 模拟以上任一类设备行为 | 测试环境 |

### 1.2 设备数量规划

| 设备类型 | 初期接入数量 | 系统上限 | 备注 |
|---|---|---|---|
| 智慧航显 | 2-3台 | 5台 | 覆盖主要引导点位 |
| 智能行李测量设备 | 1-2台 | 3台 | 值机区域部署 |
| 航延屏 | 1-2台 | 3台 | 候机区部署 |
| 移动服务机器人 | 2-3台 | 5台 | 移动服务为主 |
| 仿真体 | 2-3个 | 4个 | 测试验证使用 |
| **合计** | **8-13个** | **20个** | 初期不超过10个 |

---

## 2. 能力类型定义

### 2.1 八类标准能力

系统预置8类标准能力类型，每类能力具有标准的输入输出参数定义。

| 能力类型编码 | 能力类型名称 | 能力描述 | 典型应用场景 |
|---|---|---|---|
| CAP_INFO_DISPLAY | 综合信息展示 | 在显示设备上展示文字、图片、视频等多媒体信息 | 航班信息、导航路线、欢迎语 |
| CAP_BAGGAGE_MEASURE | 行李尺寸重量测量 | 自动测量行李的长宽高尺寸和重量 | 值机行李检查 |
| CAP_OVERSIZE_ALERT | 超规事件上报 | 检测并上报行李超规事件 | 超规行李处置流程触发 |
| CAP_FLIGHT_UPDATE | 航班变更信息发布 | 发布航班延误、登机口变更等信息 | 航班延误通知 |
| CAP_NAVIGATION | 空间引导 | 提供从当前位置到目标位置的导航引导 | 旅客找不到登机口 |
| CAP_ESCORT | 陪同服务 | 陪同旅客移动到目标位置 | 特殊旅客服务 |
| CAP_NOTIFICATION | 现场通知 | 在指定位置播报语音或展示文字通知 | 紧急广播、寻人通知 |
| CAP_SIM_STATUS | 仿真状态生成 | 生成模拟的设备状态和执行结果 | 测试验证 |

### 2.2 能力参数规范

#### 2.2.1 CAP_INFO_DISPLAY（综合信息展示）

**输入参数：**

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| contentType | String | 是 | 内容类型：TEXT/IMAGE/VIDEO/HTML |
| contentData | String | 是 | 内容数据（文本内容或资源URL） |
| displayDuration | Integer | 是 | 展示时长（秒），取值范围5-300 |
| displayPosition | String | 否 | 展示位置（屏幕区域），默认全屏 |

**输出参数：**

| 参数名 | 类型 | 说明 |
|---|---|---|
| displayStatus | String | 展示状态：SUCCESS/TIMEOUT/DEVICE_ERROR |
| actualDuration | Integer | 实际展示时长（秒） |
| errorMessage | String | 错误信息（失败时返回） |

#### 2.2.2 CAP_BAGGAGE_MEASURE（行李尺寸重量测量）

**输入参数：**

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| measureMode | String | 是 | 测量模式：AUTO（自动）/MANUAL（手动触发） |
| timeout | Integer | 是 | 测量超时时间（秒），取值范围10-60 |

**输出参数：**

| 参数名 | 类型 | 说明 |
|---|---|---|
| length | Float | 长度（厘米） |
| width | Float | 宽度（厘米） |
| height | Float | 高度（厘米） |
| weight | Float | 重量（千克） |
| isOversize | Boolean | 是否超规（根据预设阈值判断） |
| measureStatus | String | 测量状态：SUCCESS/TIMEOUT/NO_OBJECT |

#### 2.2.3 CAP_OVERSIZE_ALERT（超规事件上报）

**输入参数：**

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| baggageInfo | Object | 是 | 行李信息（尺寸、重量） |
| passengerInfo | Object | 否 | 旅客信息（姓名、航班号） |
| alertLevel | String | 是 | 告警级别：WARNING/ERROR |

**输出参数：**

| 参数名 | 类型 | 说明 |
|---|---|---|
| alertId | String | 告警事件ID |
| reportStatus | String | 上报状态：SUCCESS/FAILED |
| reportTime | String | 上报时间（ISO 8601格式） |

#### 2.2.4 CAP_FLIGHT_UPDATE（航班变更信息发布）

**输入参数：**

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| flightNumber | String | 是 | 航班号 |
| updateType | String | 是 | 变更类型：DELAY/GATE_CHANGE/CANCEL |
| updateContent | String | 是 | 变更内容描述 |
| displayDuration | Integer | 是 | 展示时长（秒），取值范围10-600 |

**输出参数：**

| 参数名 | 类型 | 说明 |
|---|---|---|
| publishStatus | String | 发布状态：SUCCESS/FAILED |
| publishTime | String | 发布时间 |

#### 2.2.5 CAP_NAVIGATION（空间引导）

**输入参数：**

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| targetLocation | String | 是 | 目标位置编码（如：GATE_A05） |
| routePreference | String | 否 | 路线偏好：SHORTEST/BARRIER_FREE（无障碍） |

**输出参数：**

| 参数名 | 类型 | 说明 |
|---|---|---|
| routeGenerated | Boolean | 路线是否生成成功 |
| estimatedDistance | Float | 预计距离（米） |
| estimatedDuration | Integer | 预计时长（秒） |
| waypointCount | Integer | 路径点数量 |

#### 2.2.6 CAP_ESCORT（陪同服务）

**输入参数：**

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| targetLocation | String | 是 | 目标位置编码 |
| escortMode | String | 是 | 陪同模式：LEAD（前导）/FOLLOW（跟随） |
| maxDuration | Integer | 是 | 最大陪同时长（秒），取值范围60-1800 |

**输出参数：**

| 参数名 | 类型 | 说明 |
|---|---|---|
| arrivalStatus | String | 到达状态：ARRIVED/TIMEOUT/LOST_TARGET |
| actualDistance | Float | 实际行驶距离（米） |
| actualDuration | Integer | 实际陪同时长（秒） |

#### 2.2.7 CAP_NOTIFICATION（现场通知）

**输入参数：**

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| notificationType | String | 是 | 通知类型：VOICE/TEXT/BOTH |
| notificationContent | String | 是 | 通知内容 |
| repeatCount | Integer | 是 | 重复次数，取值范围1-5 |

**输出参数：**

| 参数名 | 类型 | 说明 |
|---|---|---|
| notificationStatus | String | 通知状态：SUCCESS/FAILED |
| actualRepeatCount | Integer | 实际播报次数 |

#### 2.2.8 CAP_SIM_STATUS（仿真状态生成）

**输入参数：**

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| simulatedCapability | String | 是 | 模拟的能力类型编码 |
| simulatedResult | String | 是 | 模拟的执行结果：SUCCESS/FAILED/TIMEOUT |
| simulatedDelay | Integer | 否 | 模拟延迟（毫秒），默认500 |

**输出参数：**

| 参数名 | 类型 | 说明 |
|---|---|---|
| simulationStatus | String | 仿真状态：SIMULATED |
| returnedData | Object | 模拟返回的数据 |

---

## 3. 五类设备能力边界

### 3.1 智慧航显（SMART_DISPLAY）

**支持的能力类型：**

| 能力类型编码 | 能力类型名称 | 优先级 | 说明 |
|---|---|---|---|
| CAP_INFO_DISPLAY | 综合信息展示 | 核心能力 | 支持文字、图片、视频、HTML展示 |
| CAP_FLIGHT_UPDATE | 航班变更信息发布 | 核心能力 | 专用于航班信息发布 |
| CAP_NAVIGATION | 空间引导 | 扩展能力 | 展示导航路线图 |

**不支持的能力类型：**
- ❌ CAP_BAGGAGE_MEASURE（无测量硬件）
- ❌ CAP_OVERSIZE_ALERT（无检测能力）
- ❌ CAP_ESCORT（固定设备无法移动）
- ❌ CAP_NOTIFICATION（无语音播报硬件，可改为文字展示）

**能力约束：**
- 同一时刻只能展示一条内容
- 不支持触摸交互（单向信息展示）
- 展示内容需符合机场信息发布规范

**典型应用场景：**
1. 显示登机口信息
2. 发布航班延误通知
3. 展示旅客导航路线
4. 播放机场宣传视频

---

### 3.2 智能行李测量设备（BAGGAGE_SCANNER）

**支持的能力类型：**

| 能力类型编码 | 能力类型名称 | 优先级 | 说明 |
|---|---|---|---|
| CAP_BAGGAGE_MEASURE | 行李尺寸重量测量 | 核心能力 | 自动测量长宽高和重量 |
| CAP_OVERSIZE_ALERT | 超规事件上报 | 核心能力 | 自动判断超规并上报 |

**不支持的能力类型：**
- ❌ CAP_INFO_DISPLAY（无显示屏幕）
- ❌ CAP_FLIGHT_UPDATE（专用测量设备）
- ❌ CAP_NAVIGATION（固定设备）
- ❌ CAP_ESCORT（固定设备）
- ❌ CAP_NOTIFICATION（无播报硬件）

**能力约束：**
- 行李必须放置在测量平台上
- 测量精度：尺寸±2cm，重量±0.5kg
- 单次测量时间不超过30秒
- 超规阈值：尺寸>158cm（三边之和），重量>32kg

**典型应用场景：**
1. 值机柜台行李检查
2. 超规行李自动检测
3. 行李数据采集统计

---

### 3.3 航延屏（FLIGHT_DELAY_BOARD）

**支持的能力类型：**

| 能力类型编码 | 能力类型名称 | 优先级 | 说明 |
|---|---|---|---|
| CAP_FLIGHT_UPDATE | 航班变更信息发布 | 核心能力 | 专用于航班延误信息 |
| CAP_INFO_DISPLAY | 综合信息展示 | 扩展能力 | 显示其他通知信息 |

**不支持的能力类型：**
- ❌ CAP_BAGGAGE_MEASURE（无测量硬件）
- ❌ CAP_OVERSIZE_ALERT（无检测能力）
- ❌ CAP_NAVIGATION（专用于航班信息）
- ❌ CAP_ESCORT（固定设备）
- ❌ CAP_NOTIFICATION（无语音硬件）

**能力约束：**
- 优先展示航班延误信息
- 内容需符合民航信息发布规范
- 自动刷新航班状态（每5分钟）

**典型应用场景：**
1. 发布航班延误通知
2. 显示登机口变更信息
3. 展示航班取消通知

---

### 3.4 移动服务机器人（MOBILE_ROBOT）

**支持的能力类型：**

| 能力类型编码 | 能力类型名称 | 优先级 | 说明 |
|---|---|---|---|
| CAP_NAVIGATION | 空间引导 | 核心能力 | 自主导航到目标位置 |
| CAP_ESCORT | 陪同服务 | 核心能力 | 陪同旅客移动 |
| CAP_NOTIFICATION | 现场通知 | 核心能力 | 语音播报和屏幕展示 |
| CAP_INFO_DISPLAY | 综合信息展示 | 扩展能力 | 机器人屏幕展示信息 |

**不支持的能力类型：**
- ❌ CAP_BAGGAGE_MEASURE（无测量硬件）
- ❌ CAP_OVERSIZE_ALERT（无检测能力）
- ❌ CAP_FLIGHT_UPDATE（非专用信息发布设备）

**能力约束：**
- 移动速度：0.5-1.5 m/s
- 避障距离：≥30cm
- 单次任务移动距离不超过500米
- 不得进入禁入区域（安检区、行李分拣区等）
- 运动安全由设备本体控制器负责，平台不下发运动安全控制指令

**典型应用场景：**
1. 引导旅客找登机口
2. 陪同老人、儿童等特殊旅客
3. 现场寻人广播
4. 物品运送（如轮椅）

---

### 3.5 仿真体（SIMULATOR）

**支持的能力类型：**

| 能力类型编码 | 能力类型名称 | 优先级 | 说明 |
|---|---|---|---|
| CAP_SIM_STATUS | 仿真状态生成 | 核心能力 | 模拟任意设备类型的能力 |
| **继承能力** | — | — | 根据模拟的设备类型自动继承 |

**能力继承规则：**
- 仿真体创建时必须选择模拟的设备类型（智慧航显/行李测量设备/航延屏/移动服务机器人）
- 自动继承所选类型的全部能力边界
- 能力执行时返回模拟结果，不实际操控硬件

**能力约束：**
- 不得配置为"全能仿真体"（必须选择模拟类型）
- 仿真延迟可配置（默认500ms）
- 仅用于测试验证，不参与生产任务

**典型应用场景：**
1. 功能测试（无需真实设备）
2. 压力测试（模拟多设备并发）
3. 异常场景模拟（模拟设备离线、超时等）

---

## 4. 能力约束规则

### 4.1 全局约束

| 约束类型 | 约束规则 | 说明 |
|---|---|---|
| 能力唯一性 | 同一设备内，能力编码必须唯一 | 防止能力定义冲突 |
| 能力测试 | 能力启用前必须通过模拟调用测试 | 确保能力可用 |
| 能力类型约束 | 设备实例的能力类型必须在其类型边界内 | 不得配置越界能力 |
| 参数完整性 | 能力定义必须包含全部必填输入参数 | 确保能力可调用 |
| 输出可验证 | 能力必须定义输出参数用于完成条件判定 | 支持任务状态判断 |

### 4.2 设备类型约束矩阵

| 设备类型 | CAP_INFO_DISPLAY | CAP_BAGGAGE_MEASURE | CAP_OVERSIZE_ALERT | CAP_FLIGHT_UPDATE | CAP_NAVIGATION | CAP_ESCORT | CAP_NOTIFICATION | CAP_SIM_STATUS |
|---|---|---|---|---|---|---|---|---|
| 智慧航显 | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 智能行李测量设备 | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 航延屏 | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 移动服务机器人 | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| 仿真体 | 继承 | 继承 | 继承 | 继承 | 继承 | 继承 | 继承 | ✅ |

---

## 5. 能力模板库

### 5.1 智慧航显标准能力模板

#### 模板1：航班信息展示

```json
{
  "capabilityCode": "SMARTDISPLAY_FLIGHT_INFO",
  "capabilityName": "航班信息展示",
  "capabilityType": "CAP_INFO_DISPLAY",
  "inputParams": [
    {"name": "contentType", "type": "String", "required": true, "defaultValue": "HTML"},
    {"name": "contentData", "type": "String", "required": true},
    {"name": "displayDuration", "type": "Integer", "required": true, "defaultValue": 30}
  ],
  "outputParams": [
    {"name": "displayStatus", "type": "String"},
    {"name": "actualDuration", "type": "Integer"}
  ],
  "description": "在智慧航显上展示航班信息HTML页面"
}
```

#### 模板2：导航路线展示

```json
{
  "capabilityCode": "SMARTDISPLAY_ROUTE_GUIDE",
  "capabilityName": "导航路线展示",
  "capabilityType": "CAP_NAVIGATION",
  "inputParams": [
    {"name": "targetLocation", "type": "String", "required": true},
    {"name": "routePreference", "type": "String", "required": false, "defaultValue": "SHORTEST"}
  ],
  "outputParams": [
    {"name": "routeGenerated", "type": "Boolean"},
    {"name": "waypointCount", "type": "Integer"}
  ],
  "description": "在智慧航显上展示到目标位置的导航路线"
}
```

### 5.2 智能行李测量设备标准能力模板

#### 模板3：自动行李测量

```json
{
  "capabilityCode": "BAGGAGE_AUTO_MEASURE",
  "capabilityName": "自动行李测量",
  "capabilityType": "CAP_BAGGAGE_MEASURE",
  "inputParams": [
    {"name": "measureMode", "type": "String", "required": true, "defaultValue": "AUTO"},
    {"name": "timeout", "type": "Integer", "required": true, "defaultValue": 30}
  ],
  "outputParams": [
    {"name": "length", "type": "Float"},
    {"name": "width", "type": "Float"},
    {"name": "height", "type": "Float"},
    {"name": "weight", "type": "Float"},
    {"name": "isOversize", "type": "Boolean"},
    {"name": "measureStatus", "type": "String"}
  ],
  "description": "自动测量行李尺寸和重量"
}
```

### 5.3 移动服务机器人标准能力模板

#### 模板4：旅客引导

```json
{
  "capabilityCode": "ROBOT_PASSENGER_GUIDE",
  "capabilityName": "旅客引导",
  "capabilityType": "CAP_ESCORT",
  "inputParams": [
    {"name": "targetLocation", "type": "String", "required": true},
    {"name": "escortMode", "type": "String", "required": true, "defaultValue": "LEAD"},
    {"name": "maxDuration", "type": "Integer", "required": true, "defaultValue": 600}
  ],
  "outputParams": [
    {"name": "arrivalStatus", "type": "String"},
    {"name": "actualDistance", "type": "Float"},
    {"name": "actualDuration", "type": "Integer"}
  ],
  "description": "引导旅客到达目标登机口"
}
```

---

## 6. 仿真体能力继承规则

### 6.1 继承机制

**步骤1：选择模拟类型**
- 创建仿真体设备时，必须从四类真实设备中选择一个作为模拟类型
- 不允许创建"无类型仿真体"

**步骤2：自动加载能力模板**
- 系统自动加载所选类型的全部标准能力模板
- 继承该类型的能力约束规则

**步骤3：能力定制**
- 配置管理员可在继承的能力模板基础上定制参数
- 不得添加该类型不支持的能力类型

**步骤4：仿真行为**
- 能力调用时，仿真体返回预设的模拟结果
- 可配置模拟延迟（模拟网络延迟、处理时间）
- 可配置失败率（模拟异常场景）

### 6.2 仿真体配置示例

**示例：模拟智慧航显的仿真体**

```json
{
  "deviceCode": "SIM_DISPLAY_001",
  "deviceName": "仿真智慧航显1号",
  "deviceType": "SIMULATOR",
  "simulatedType": "SMART_DISPLAY",
  "capabilities": [
    {
      "capabilityCode": "SIM_FLIGHT_INFO_DISPLAY",
      "capabilityType": "CAP_INFO_DISPLAY",
      "simulationConfig": {
        "simulatedDelay": 500,
        "successRate": 0.95,
        "simulatedResult": "SUCCESS"
      }
    }
  ]
}
```

### 6.3 仿真场景配置

| 仿真场景 | 配置参数 | 说明 |
|---|---|---|
| 正常场景 | successRate: 1.0 | 100%成功 |
| 网络延迟场景 | simulatedDelay: 2000-5000 | 模拟2-5秒延迟 |
| 偶发失败场景 | successRate: 0.9 | 10%失败率 |
| 设备离线场景 | deviceStatus: OFFLINE | 模拟设备离线 |
| 超时场景 | simulatedResult: TIMEOUT | 模拟执行超时 |

---

## 7. 能力扩展指南

### 7.1 新增能力类型流程

**步骤1：能力类型定义**
- 定义能力类型编码（CAP_XXX）
- 定义能力类型名称和描述
- 定义标准输入输出参数

**步骤2：设备类型适配**
- 确定哪些设备类型支持该能力
- 更新设备类型能力边界矩阵

**步骤3：能力模板创建**
- 为支持的设备类型创建标准能力模板
- 定义典型应用场景

**步骤4：系统配置更新**
- 更新能力类型下拉框选项
- 更新能力校验规则

### 7.2 能力定制注意事项

1. **参数兼容性**：定制参数时保持向后兼容
2. **约束一致性**：定制后的能力必须符合类型约束
3. **测试完整性**：定制能力必须通过模拟调用测试
4. **文档同步**：更新能力说明文档

---

**文档结束**

**相关文档**：
- [需求规格说明书V1.3 - 5.2.4A 设备类型能力边界管理](./20260901-智慧机场人工智能集群协同服务平台-需求规格说明书-V1.3.md)
- [附录A: 技术架构规范](./附录A-技术架构规范.md)
- [附录B: 接口设计规范](./附录B-接口设计规范.md)
