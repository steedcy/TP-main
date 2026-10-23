import request from './request'

// 对应附录B 6.7节任务规划与执行模块
export function submitTask(data) {
  return request.post('/tasks', data)
}

export function listTasks(params) {
  return request.get('/tasks', { params })
}

export function getTask(taskId) {
  return request.get(`/tasks/${taskId}`)
}

export function manualAction(taskId, action) {
  return request.post(`/tasks/${taskId}/manual-actions`, { action })
}

export function terminateTask(taskId, reason) {
  return request.post(`/tasks/${taskId}/terminate`, { reason, confirmed: true })
}

export function getTaskEvents(taskId) {
  return request.get(`/tasks/${taskId}/events`)
}

export function getPlanVersions(taskId) {
  return request.get(`/tasks/${taskId}/plan-versions`)
}

export function getContextSnapshots(taskId) {
  return request.get(`/tasks/${taskId}/context-snapshots`)
}

export function clarifyTask(taskId, answers) {
  return request.post(`/tasks/${taskId}/clarify`, { answers })
}

export function cancelTask(taskId, reason) {
  return request.post(`/tasks/${taskId}/cancel`, { reason })
}

// 对应5.5.1/5.5.2界面元素：步骤设备分配、指令与执行反馈
export function getStepAssignments(taskId) {
  return request.get(`/tasks/${taskId}/step-assignments`)
}

// 对应5.5.3/5.5.5异常列表
export function listTaskExceptions(params) {
  return request.get('/task-exceptions', { params })
}
