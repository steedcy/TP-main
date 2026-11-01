// node src/utils/taskProgress.check.mjs  —— 纯函数自检
import assert from 'node:assert/strict'
import { taskProgress, progressText } from './taskProgress.js'

const plan = [1, 2, 3, 4].map((stepSeq) => ({ stepSeq }))
const row = (stepSeq, stepStatus) => ({ stepSeq, stepStatus })

let p = taskProgress(plan, [row(1, 'COMPLETED'), row(2, 'EXECUTING'), row(3, 'PENDING_ASSIGNMENT'), row(4, 'PENDING_ASSIGNMENT')])
assert.deepEqual([p.total, p.completed, p.current, p.percent], [4, 1, 2, 25])
assert.equal(progressText(p), '1/4，当前步骤2')

p = taskProgress(plan, [1, 2, 3, 4].map((s) => row(s, 'COMPLETED')))
assert.deepEqual([p.completed, p.current, p.percent], [4, null, 100])
assert.equal(progressText(p), '4/4')

// 记录还没生成的步骤按待分配，总数仍取计划步骤数
p = taskProgress(plan, [row(1, 'COMPLETED')])
assert.deepEqual([p.total, p.completed, p.current], [4, 1, 2])

// 失败、冻结、跳过：不算完成，但计入总数；冻结步骤不会成为当前步
p = taskProgress(plan, [row(1, 'COMPLETED'), row(2, 'FAILED'), row(3, 'FROZEN'), row(4, 'SKIPPED')])
assert.deepEqual([p.total, p.completed, p.failed, p.skipped, p.current], [4, 1, 1, 1, null])
assert.equal(progressText(p), '1/4（跳过1，失败1）')

// 没有计划步骤时退回分配记录；两者都没有显示占位
p = taskProgress([], [row(1, 'COMPLETED'), row(2, 'EXECUTING')])
assert.deepEqual([p.total, p.completed, p.current], [2, 1, 2])
assert.equal(progressText(taskProgress([], [])), '—')
assert.equal(progressText(taskProgress(undefined, undefined)), '—')
assert.equal(progressText(null), '—')
console.log('taskProgress checks passed')
