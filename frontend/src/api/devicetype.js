import request from './request'

// 对应附录B 6.4节设备类型能力边界管理模块（5.2.4A）
export function listDeviceTypes() {
  return request.get('/device-types')
}

export function getCapabilityBoundary(deviceTypeCode) {
  return request.get(`/device-types/${deviceTypeCode}/capability-boundary`)
}

export function updateCapabilityBoundary(deviceTypeCode, data) {
  return request.put(`/device-types/${deviceTypeCode}/capability-boundary`, data)
}

export function listCapabilityTemplates(deviceTypeCode) {
  return request.get(`/device-types/${deviceTypeCode}/capability-templates`)
}

export function listDeviceTypeOverview() {
  return request.get('/device-types/overview')
}

export function exportCapabilityMatrix() {
  return request.get('/device-types/capability-matrix/export', { responseType: 'blob' })
}

export function listTemplateVersions(deviceTypeCode, templateCode) {
  return request.get(`/device-types/${deviceTypeCode}/capability-templates/${templateCode}/versions`)
}

export function createCapabilityTemplate(deviceTypeCode, data) {
  return request.post(`/device-types/${deviceTypeCode}/capability-templates`, data)
}

export function updateCapabilityTemplate(deviceTypeCode, templateCode, data) {
  return request.put(`/device-types/${deviceTypeCode}/capability-templates/${templateCode}`, data)
}

export function updateCapabilityTemplateStatus(deviceTypeCode, templateCode, status) {
  return request.post(`/device-types/${deviceTypeCode}/capability-templates/${templateCode}/status`, { status })
}

export function deleteCapabilityTemplate(deviceTypeCode, templateCode) {
  return request.delete(`/device-types/${deviceTypeCode}/capability-templates/${templateCode}`)
}

export function getCapabilityMatrix() {
  return request.get('/device-types/capability-matrix')
}

// 对应附录B 6.5节设备能力画像管理模块（5.2.4，实例层）
export function listDeviceCapabilities(deviceCode) {
  return request.get(`/devices/${deviceCode}/capabilities`)
}

export function createDeviceCapability(deviceCode, data) {
  return request.post(`/devices/${deviceCode}/capabilities`, data)
}

export function updateDeviceCapability(deviceCode, capabilityCode, data) {
  return request.put(`/devices/${deviceCode}/capabilities/${capabilityCode}`, data)
}

export function testDeviceCapability(deviceCode, capabilityCode) {
  return request.post(`/devices/${deviceCode}/capabilities/${capabilityCode}/test`)
}

export function updateDeviceCapabilityStatus(deviceCode, capabilityCode, status) {
  return request.post(`/devices/${deviceCode}/capabilities/${capabilityCode}/status`, { status })
}
