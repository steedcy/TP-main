import request from './request'

export function listSimulators() {
  return request.get('/simulators')
}

export function setSimulatorOnline(deviceCode, onlineStatus) {
  return request.post(`/simulators/${deviceCode}/online`, { onlineStatus })
}

export function setSimulatorScenario(deviceCode, scenarioResult) {
  return request.post(`/simulators/${deviceCode}/scenario`, { scenarioResult })
}

export function listSimulatorEvents(deviceCode) {
  return request.get(`/simulators/${deviceCode}/events`)
}

export function listSimulatorCommands(deviceCode) {
  return request.get(`/simulators/${deviceCode}/commands`)
}
