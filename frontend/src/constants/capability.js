// 系统预置8类标准能力类型，不可新增或删除（对应5.2.4A业务规则2、V1.4正文8.4.2节）
export const CAPABILITY_TYPES = [
  { value: 'CAP_INFO_DISPLAY', label: '综合信息展示' },
  { value: 'CAP_BAGGAGE_MEASURE', label: '行李尺寸重量测量' },
  { value: 'CAP_OVERSIZE_ALERT', label: '超规事件上报' },
  { value: 'CAP_FLIGHT_UPDATE', label: '航班变更信息发布' },
  { value: 'CAP_NAVIGATION', label: '空间引导' },
  { value: 'CAP_ESCORT', label: '陪同服务' },
  { value: 'CAP_NOTIFICATION', label: '现场通知' },
  { value: 'CAP_SIM_STATUS', label: '仿真状态生成' }
]

export function capabilityLabel(code) {
  return CAPABILITY_TYPES.find(c => c.value === code)?.label || code
}

// 系统预置5类设备类型，不可新增或删除（对应5.2.1、5.2.4A业务规则1）
export const DEVICE_TYPES = [
  { value: 'SMART_DISPLAY', label: '智慧航显' },
  { value: 'BAGGAGE_SCANNER', label: '智能行李测量设备' },
  { value: 'FLIGHT_DELAY_BOARD', label: '航延屏' },
  { value: 'MOBILE_ROBOT', label: '移动服务机器人' },
  { value: 'SIMULATOR', label: '仿真体' }
]

export function deviceTypeLabel(code) {
  return DEVICE_TYPES.find(t => t.value === code)?.label || code
}

export const PARAM_TYPES = ['String', 'Integer', 'Boolean', 'Double']

// 基线模板意图枚举，对应5.3.1界面元素"模板意图"、附录B 6.6节templateIntent
export const TEMPLATE_INTENTS = [
  { value: 'OVERSIZE_BAGGAGE_HANDLING', label: '超规行李处置' },
  { value: 'SPECIAL_PASSENGER_SERVICE', label: '特殊旅客服务' },
  { value: 'FLIGHT_CHANGE_RESPONSE', label: '航班变更应对' },
  { value: 'EXTENDED', label: '已扩展任务定义' }
]

export function templateIntentLabel(code) {
  return TEMPLATE_INTENTS.find(t => t.value === code)?.label || code
}
