// node src/utils/situationMarkers.check.mjs
import assert from 'node:assert/strict'
import { Z, markerZIndex, isOverlapping, isOffline, offlineSummary, reportedAtClass } from './situationMarkers.js'

const dev = (o) => ({ deviceCode: 'D', agentStatus: 'ENABLED', onlineStatus: 'ONLINE', workStatus: 'IDLE', ...o })

// 层级：离线终端必须在在线机器人之上，才点得到（DEF-S3-048）
assert.ok(markerZIndex(dev({ onlineStatus: 'OFFLINE' })) > markerZIndex(dev({ workStatus: 'BUSY' })))
assert.ok(markerZIndex(dev({ workStatus: 'BUSY' })) > markerZIndex(dev({})))
assert.equal(markerZIndex(dev({ agentStatus: 'DISABLED' })), Z.offline)
// 选中的最高，不管状态
assert.equal(markerZIndex(dev({ deviceCode: 'T1' }), 'T1'), Z.selected)
assert.equal(markerZIndex(dev({ deviceCode: 'T2', onlineStatus: 'OFFLINE' }), 'T1'), Z.offline)
assert.equal(markerZIndex(dev({}), undefined), Z.online)

assert.equal(isOverlapping({ left: 50, top: 50 }, { left: 51, top: 51 }), true)
assert.equal(isOverlapping({ left: 50, top: 50 }, { left: 60, top: 50 }), false)
assert.equal(isOverlapping(null, { left: 1, top: 1 }), false)

// 离线判断：停用的代理不算“离线”（它本来就不在线），在线的也不算
assert.equal(isOffline(dev({ onlineStatus: 'OFFLINE' })), true)
assert.equal(isOffline(dev({})), false)
assert.equal(isOffline(dev({ agentStatus: 'DISABLED', onlineStatus: 'OFFLINE' })), false)

// 离线提示：原因码、任务影响、缺事件时的兜底
let s = offlineSummary(dev({ onlineStatus: 'OFFLINE', currentTaskId: 59,
  offline: { reasonCode: 'ERR_HEARTBEAT_TIMEOUT', affectsTask: true, offlineAt: '2026-10-31T10:00:00' } }))
assert.equal(s.reason, 'ERR_HEARTBEAT_TIMEOUT')
assert.match(s.impact, /影响任务 59/)
assert.equal(s.offlineAt, '2026-10-31T10:00:00')
s = offlineSummary(dev({ onlineStatus: 'OFFLINE', offline: { reasonCode: 'ERR_HEARTBEAT_TIMEOUT', affectsTask: false } }))
assert.equal(s.impact, '不影响任务')
s = offlineSummary(dev({ onlineStatus: 'OFFLINE' }))
assert.equal(s.reason, '未记录离线原因')
assert.equal(s.impact, '不影响任务')
assert.equal(offlineSummary(dev({})), null)
assert.equal(offlineSummary(undefined), null)

assert.equal(reportedAtClass(dev({ onlineStatus: 'OFFLINE' })), 'reported-at-offline')
assert.equal(reportedAtClass(dev({})), '')
console.log('situationMarkers checks passed')
