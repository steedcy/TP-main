// node src/utils/planSummary.check.mjs
import assert from 'node:assert/strict'
import { TOTAL_STEP_QUOTA, stepCount, quotaSummary, quotaText, formatInputParams, paramSourceText } from './planSummary.js'

assert.equal(TOTAL_STEP_QUOTA, 5)
const plan = (n) => ({ planSteps: Array.from({ length: n }, (_, i) => ({ stepSeq: i + 1 })) })
assert.equal(stepCount(plan(4)), 4)
assert.equal(stepCount(undefined), 0)
assert.equal(stepCount({ planSteps: null }), 0)
assert.deepEqual(quotaSummary(plan(4)), { used: 4, total: 5, remaining: 1, exceededBy: 0 })
assert.deepEqual(quotaSummary(plan(5)), { used: 5, total: 5, remaining: 0, exceededBy: 0 })
assert.deepEqual(quotaSummary(plan(0)), { used: 0, total: 5, remaining: 5, exceededBy: 0 })
// 超限版本剩余额度为 0，不出现负数
assert.deepEqual(quotaSummary(plan(7)), { used: 7, total: 5, remaining: 0, exceededBy: 2 })
assert.equal(quotaText(plan(4)), '4 步 / 上限 5 步，剩余额度 1 步')
assert.equal(quotaText(plan(6)), '6 步 / 上限 5 步，剩余额度 0 步（超出 1 步）')

assert.equal(formatInputParams({ targetLocation: 'F2_GATE', timeout: 30 }), 'targetLocation=F2_GATE；timeout=30')
assert.equal(formatInputParams({ a: { x: 1 } }), 'a={"x":1}')
assert.equal(formatInputParams({ flag: false, n: 0 }), 'flag=false；n=0', '假值不能被吞掉')
assert.equal(formatInputParams({}), '—')
assert.equal(formatInputParams(null), '—')
assert.equal(formatInputParams([1, 2]), '—')
assert.equal(formatInputParams({ k: 'x'.repeat(300) }).length, 161)

assert.equal(paramSourceText({ inputParams: { loc: 'TEMPLATE_INPUT.targetLocation' } }), 'TEMPLATE_INPUT')
assert.equal(paramSourceText({ inputParams: { loc: 'STEP2_OUTPUT.waypoints' } }), 'STEP2_OUTPUT')
assert.equal(paramSourceText({ inputParams: { baggageLocation: 'F2' } }, { baggageLocation: 'F2' }), '场景参数')
assert.equal(paramSourceText({ inputParams: { speed: 1 } }, {}), '规划给出')
assert.equal(paramSourceText({ inputParams: { a: 'TEMPLATE_INPUT.x', b: 1 } }), 'TEMPLATE_INPUT、规划给出')
assert.equal(paramSourceText({}), '—')
assert.equal(paramSourceText(undefined), '—')
console.log('planSummary checks passed')
