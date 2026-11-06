// node src/utils/taskListView.check.mjs  —— 纯函数自检
import assert from 'node:assert/strict'
import { todayRange, shouldDefaultToToday, buildListParams, formatLocal, statusTagColor, rowClassName } from './taskListView.js'

// 默认今日：00:00:00 到 23:59:59，跨月跨年边界也正确
let [s, e] = todayRange(new Date(2026, 9, 31, 15, 20, 5))
assert.equal(formatLocal(s), '2026-10-31T00:00:00')
assert.equal(formatLocal(e), '2026-10-31T23:59:59')
;[s, e] = todayRange(new Date(2026, 11, 31, 0, 0, 0))
assert.equal(formatLocal(s), '2026-12-31T00:00:00')
assert.equal(formatLocal(e), '2026-12-31T23:59:59')
;[s, e] = todayRange(new Date(2027, 0, 1, 23, 59, 59))
assert.equal(formatLocal(s), '2027-01-01T00:00:00')

// 总览跳转带条件时不叠加“今日”
assert.equal(shouldDefaultToToday({}), true)
assert.equal(shouldDefaultToToday(), true)
assert.equal(shouldDefaultToToday({ status: 'PENDING_MANUAL' }), false)
assert.equal(shouldDefaultToToday({ taskFamily: 'OVERSIZE_BAGGAGE_HANDLING' }), false)
assert.equal(shouldDefaultToToday({ taskCode: 'T1' }), false)
assert.equal(shouldDefaultToToday({ goalKeyword: '航班' }), false)
assert.equal(shouldDefaultToToday({ other: 'x' }), true)

// 请求参数：空白不传，关键字去首尾空格
let p = buildListParams({ status: '', taskCode: '  ', taskFamily: undefined, goalKeyword: '   ', range: [] })
assert.deepEqual(p, { status: undefined, taskCode: undefined, taskFamily: undefined, goalKeyword: undefined })
p = buildListParams({ status: 'PENDING_MANUAL', taskCode: ' T7 ', taskFamily: 'X', goalKeyword: ' 航班延误 ',
  range: [new Date(2026, 9, 31, 0, 0, 0), new Date(2026, 9, 31, 23, 59, 59)] })
assert.equal(p.goalKeyword, '航班延误')
assert.equal(p.taskCode, 'T7')
assert.equal(p.createdFrom, '2026-10-31T00:00:00')
assert.equal(p.createdTo, '2026-10-31T23:59:59')
// 范围不完整则不传时间
// 选择器给出的字符串原样传递
p = buildListParams({ range: ['2026-10-31T00:00:00', '2026-10-31T23:59:59'] })
assert.equal(p.createdFrom, '2026-10-31T00:00:00')
assert.equal(p.createdTo, '2026-10-31T23:59:59')
assert.equal(buildListParams({ range: [new Date()] }).createdFrom, undefined)
assert.equal(buildListParams({ range: [null, null] }).createdFrom, undefined)

// 分页参数正确传递（DEF-S3-115）
p = buildListParams({ page: 2, size: 20 })
assert.equal(p.page, 2)
assert.equal(p.size, 20)

// 状态强调：待人工与已完成明显不同
assert.equal(statusTagColor('PENDING_MANUAL'), 'orange')
assert.notEqual(statusTagColor('PENDING_MANUAL'), statusTagColor('COMPLETED'))
assert.equal(statusTagColor('FAILED'), 'red')
assert.equal(statusTagColor('UNKNOWN'), undefined)
assert.equal(rowClassName({ status: 'PENDING_MANUAL' }), 'row-pending-manual')
assert.equal(rowClassName({ status: 'COMPLETED' }), '')
assert.equal(rowClassName(undefined), '')
console.log('taskListView checks passed')
