// node src/utils/situationMarkers.check.mjs
import assert from 'node:assert/strict'
import {
  Z,
  markerZIndex,
  parseMarkerPoint,
  isOverlapping,
  findOverlappingDevices,
  hasSameTierOverlap,
  isOffline,
  offlineSummary,
  reportedAtClass
} from './situationMarkers.js'

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

// 坐标解析与重叠检测（DEF-S3-048）
const d1 = dev({ deviceCode: 'G145_DISPLAY', location: { x: 450, y: 260 } })
const d2 = dev({ deviceCode: 'G180_ROBOT', location: { x: 450, y: 260 } })
const d3 = dev({ deviceCode: 'G175_FLIGHT', location: { x: 850, y: 360 } })
const dInvalid = dev({ deviceCode: 'D_INV', location: { x: -1, y: 200 } })

assert.equal(parseMarkerPoint(dInvalid), null)
assert.ok(parseMarkerPoint(d1) !== null)
assert.equal(Number(parseMarkerPoint(d1).left.toFixed(4)), Number((450 / 1260 * 100).toFixed(4)))

const list = [d1, d2, d3]
const overlapsForD1 = findOverlappingDevices(d1, list)
assert.equal(overlapsForD1.length, 2)
assert.deepEqual(overlapsForD1.map(d => d.deviceCode), ['G145_DISPLAY', 'G180_ROBOT'])

const overlapsForD3 = findOverlappingDevices(d3, list)
assert.equal(overlapsForD3.length, 1)
assert.equal(overlapsForD3[0].deviceCode, 'G175_FLIGHT')

// 同状态/同层级重叠判定（DEF-S3-048）
// 1. 同为 ONLINE/IDLE 且坐标相同 -> 必须触发同状态重叠选择器
assert.equal(hasSameTierOverlap(d1, list), true)
assert.equal(hasSameTierOverlap(d2, list), true)
assert.equal(hasSameTierOverlap(d3, list), false)

// 2. 状态不同（一个离线一个在线）-> 离线拥有更高层级（Z.offline > Z.online），按层级优先直接点选，不阻碍独立离线分支
const d1Offline = dev({ deviceCode: 'G145_DISPLAY', onlineStatus: 'OFFLINE', location: { x: 450, y: 260 } })
const mixedList = [d1Offline, d2, d3]
assert.equal(hasSameTierOverlap(d1Offline, mixedList), false)
assert.equal(hasSameTierOverlap(d2, mixedList), false)

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
// 动态重叠候选集同步与成员移离验证（DEF-S3-118）
const anchor = { location: { x: 450, y: 260 } }
// 1. 初始状态：两设备在 (450, 260)，候选包含两者
const initialCandidates = findOverlappingDevices(anchor, [d1, d2, d3])
assert.equal(initialCandidates.length, 2)
assert.deepEqual(initialCandidates.map(d => d.deviceCode), ['G145_DISPLAY', 'G180_ROBOT'])

// 2. 状态更新：G145_DISPLAY 发生心跳超时离线，候选列表中应即时体现离线状态与原因
const offlineCandidates = findOverlappingDevices(anchor, [d1Offline, d2, d3])
assert.equal(offlineCandidates.length, 2)
const foundOffline = offlineCandidates.find(d => d.deviceCode === 'G145_DISPLAY')
assert.equal(isOffline(foundOffline), true)

// 3. 成员移离：G145_DISPLAY 经协议上报移至 (100, 800)，候选列表应自动剔除已移离成员，仅保留留在原坐标的 G180_ROBOT
const d1Moved = dev({ deviceCode: 'G145_DISPLAY', location: { x: 100, y: 800 } })
const movedCandidates = findOverlappingDevices(anchor, [d1Moved, d2, d3])
assert.equal(movedCandidates.length, 1)
assert.equal(movedCandidates[0].deviceCode, 'G180_ROBOT')

// 4. 新成员加入：新设备 G199 移动到 (450, 260)，候选列表应即时反映新增重叠
const dNew = dev({ deviceCode: 'G199_NEW', location: { x: 450, y: 260 } })
const addedCandidates = findOverlappingDevices(anchor, [d1, d2, d3, dNew])
assert.equal(addedCandidates.length, 3)
assert.ok(addedCandidates.some(d => d.deviceCode === 'G199_NEW'))

console.log('situationMarkers checks passed')
