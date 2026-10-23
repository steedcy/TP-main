import request from './request'

// 对应附录B 6.3节设备档案与设备代理模块
export function listDevices(params) {
  return request.get('/devices', { params })
}

export function getDevice(deviceCode) {
  return request.get(`/devices/${deviceCode}`)
}

export function createDevice(data) {
  return request.post('/devices', data)
}

export function updateDevice(deviceCode, data) {
  return request.put(`/devices/${deviceCode}`, data)
}

export function testConnection(deviceCode) {
  return request.post(`/devices/${deviceCode}/connection-test`)
}

export function updateDeviceStatus(deviceCode, status) {
  return request.post(`/devices/${deviceCode}/status`, { status })
}

export function deleteDevice(deviceCode) {
  return request.delete(`/devices/${deviceCode}`)
}

export function listAgents(params) {
  return request.get('/device-agents', { params })
}

export function createAgent(deviceCode) {
  return request.post('/device-agents', { deviceCode })
}

export function getAgent(agentId) {
  return request.get(`/device-agents/${agentId}`)
}

export function disableAgent(agentId) {
  return request.post(`/device-agents/${agentId}/disable`, { confirmed: true })
}
