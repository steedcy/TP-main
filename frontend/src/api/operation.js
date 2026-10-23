import request from './request'

// 对应5.7.2操作记录：按操作人/操作类型/操作结果/时间范围任意组合筛选
export function listOperationLogs(params) {
  return request.get('/operation-logs', { params })
}
