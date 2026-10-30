// node src/utils/timeline.check.mjs  —— 无测试框架时的纯函数自检，失败时以非零码退出
import assert from 'node:assert/strict'
import { timelineResult, timelineReason, timelineOutcome, EMPTY_CELL } from './timeline.js'

const rows = [
  { name: '失败', rec: { result: 'FAILED', reasonCode: 'GPT_FAILED' }, result: 'FAILED', reason: 'GPT_FAILED', outcome: 'FAILED（GPT_FAILED）' },
  { name: '超时', rec: { result: 'TIMED_OUT', reasonCode: 'SIMULATED_TIMEOUT' }, result: 'TIMED_OUT', reason: 'SIMULATED_TIMEOUT', outcome: 'TIMED_OUT（SIMULATED_TIMEOUT）' },
  { name: '拒绝', rec: { result: 'REJECTED', reasonCode: 'DEVICE_BUSY' }, result: 'REJECTED', reason: 'DEVICE_BUSY', outcome: 'REJECTED（DEVICE_BUSY）' },
  { name: '成功带原因码', rec: { result: 'SUCCEEDED', reasonCode: 'DEVICE_SUCCESS' }, result: 'SUCCEEDED', reason: 'DEVICE_SUCCESS', outcome: 'SUCCEEDED（DEVICE_SUCCESS）' },
  { name: '成功无原因码', rec: { result: 'ACCEPTED', reasonCode: null }, result: 'ACCEPTED', reason: EMPTY_CELL, outcome: 'ACCEPTED' },
  { name: '只有原因码的事件', rec: { result: null, reasonCode: 'DEVICE_BIND_FAILED' }, result: EMPTY_CELL, reason: 'DEVICE_BIND_FAILED', outcome: 'DEVICE_BIND_FAILED' },
  { name: '两者都没有', rec: { result: null, reasonCode: null }, result: EMPTY_CELL, reason: EMPTY_CELL, outcome: EMPTY_CELL },
  { name: '缺字段', rec: {}, result: EMPTY_CELL, reason: EMPTY_CELL, outcome: EMPTY_CELL },
  { name: '空记录', rec: undefined, result: EMPTY_CELL, reason: EMPTY_CELL, outcome: EMPTY_CELL }
]
for (const r of rows) {
  assert.equal(timelineResult(r.rec), r.result, `${r.name} 结果`)
  assert.equal(timelineReason(r.rec), r.reason, `${r.name} 原因码`)
  assert.equal(timelineOutcome(r.rec), r.outcome, `${r.name} 合并`)
}
console.log(`timeline display checks passed: ${rows.length}`)
