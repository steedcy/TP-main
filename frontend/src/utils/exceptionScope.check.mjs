// node src/utils/exceptionScope.check.mjs  —— 纯函数自检
import assert from 'node:assert/strict'
import { inScope, scopeCounts, scopeForStatus } from './exceptionScope.js'

const r = (exceptionStatus) => ({ exceptionStatus })
const rows = [r('PENDING'), r('PENDING'), r('PROCESSING'), r('RESOLVED'), r('RESOLVED'), r('RESOLVED'), r('IGNORED')]

assert.deepEqual(scopeCounts(rows), { active: 3, history: 4, all: 7 })
assert.equal(rows.filter((x) => inScope(x, 'active')).length, 3)
assert.equal(rows.filter((x) => inScope(x, 'history')).length, 4)
assert.equal(rows.filter((x) => inScope(x, 'all')).length, 7)

// 与任务83的现象一致：三条已处置不再混在待处理里
const task83 = [r('RESOLVED'), r('RESOLVED'), r('RESOLVED'), r('PENDING'), r('PENDING')]
assert.equal(task83.filter((x) => inScope(x, 'active')).length, 2)
assert.equal(task83.filter((x) => inScope(x, 'history')).length, 3)

// 未知或缺失状态按待处理，不被悄悄归档
assert.equal(inScope(r('SOMETHING_NEW'), 'active'), true)
assert.equal(inScope(r('SOMETHING_NEW'), 'history'), false)
assert.equal(inScope({}, 'active'), true)
assert.equal(inScope(undefined, 'history'), false)

assert.deepEqual(scopeCounts([]), { active: 0, history: 0, all: 0 })
assert.deepEqual(scopeCounts(undefined), { active: 0, history: 0, all: 0 })

assert.equal(scopeForStatus(undefined), 'active')
assert.equal(scopeForStatus('PENDING'), 'active')
assert.equal(scopeForStatus('PROCESSING'), 'active')
assert.equal(scopeForStatus('RESOLVED'), 'history')
assert.equal(scopeForStatus('IGNORED'), 'history')
console.log('exceptionScope checks passed')
