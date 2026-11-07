// 态势地图的标记层级与离线提示（SRS_F023，DEF-S3-047、048）。纯函数，便于自检。

// 标记层级：基础 2。坐标接近时后渲染的会盖住前面的，导致点不到被遮挡的标记（尤其是离线的终端）。
// 所以：离线 > 忙碌 > 在线空闲 依次抬高，选中的最高；悬停时再抬一级（由样式处理）。
export const Z = { base: 2, online: 2, busy: 3, offline: 4, selected: 6 }

export function markerZIndex(device, selectedCode) {
  if (selectedCode && device.deviceCode === selectedCode) return Z.selected
  if (device.agentStatus !== 'ENABLED' || device.onlineStatus !== 'ONLINE') return Z.offline
  return device.workStatus === 'BUSY' ? Z.busy : Z.online
}

// 两点（百分比坐标）是否近到会互相遮挡。阈值按地图百分比，约一个标记的宽度。
export function isOverlapping(a, b, threshold = 2.5) {
  if (!a || !b) return false
  return Math.abs(a.left - b.left) < threshold && Math.abs(a.top - b.top) < threshold
}

export function isOffline(device) {
  return device?.agentStatus === 'ENABLED' && device?.onlineStatus !== 'ONLINE'
}

// 离线提示文案：原因码 + 是否影响任务。没有离线事件时（例如手工置离线）给出明确的“未记录”而不是空白。
export function offlineSummary(device) {
  if (!isOffline(device)) return null
  const info = device.offline || {}
  const reason = info.reasonCode || '未记录离线原因'
  const impact = info.affectsTask === true
    ? `影响任务${device.currentTaskId != null ? ' ' + device.currentTaskId : ''}（等待异常恢复）`
    : '不影响任务'
  return { reason, impact, offlineAt: info.offlineAt || null, detail: info.detail || null }
}

// 最后上报时间的强调：离线的代理上报时间用醒目样式。
export function reportedAtClass(device) {
  return isOffline(device) ? 'reported-at-offline' : ''
}
