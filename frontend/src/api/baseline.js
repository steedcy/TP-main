import request from './request'

// 对应附录B 6.6节基线服务模板模块（5.3.1、5.3.2）
export function listBaselineTemplates() {
  return request.get('/baseline-templates')
}

export function getBaselineTemplate(templateId) {
  return request.get(`/baseline-templates/${templateId}`)
}

export function createBaselineTemplate(data) {
  return request.post('/baseline-templates', data)
}

export function updateBaselineTemplate(templateId, data) {
  return request.put(`/baseline-templates/${templateId}`, data)
}

export function dryRunBaselineTemplate(templateId, data) {
  return request.post(`/baseline-templates/${templateId}/dry-run`, data)
}

export function enableBaselineTemplate(templateId) {
  return request.post(`/baseline-templates/${templateId}/enable`)
}

export function disableBaselineTemplate(templateId) {
  return request.post(`/baseline-templates/${templateId}/disable`)
}

export function deleteBaselineTemplate(templateId) {
  return request.delete(`/baseline-templates/${templateId}`)
}

export function getBaselineDryRun(templateId, taskId) {
  return request.get(`/baseline-templates/${templateId}/dry-runs/${taskId}`)
}
export function cancelBaselineDryRun(templateId, taskId) {
  return request.post(`/baseline-templates/${templateId}/dry-runs/${taskId}/cancel`)
}
