import request from './request'

// 对应5.6.1旅客服务任务定义管理
export function listTaskDefinitions() {
  return request.get('/task-definitions')
}

export function getTaskDefinition(id) {
  return request.get(`/task-definitions/${id}`)
}

export function createTaskDefinition(data) {
  return request.post('/task-definitions', data)
}

export function updateTaskDefinition(id, data) {
  return request.put(`/task-definitions/${id}`, data)
}

export function enableTaskDefinition(id) {
  return request.post(`/task-definitions/${id}/enable`)
}

export function disableTaskDefinition(id) {
  return request.post(`/task-definitions/${id}/disable`)
}

export function deleteTaskDefinition(id) {
  return request.delete(`/task-definitions/${id}`)
}
