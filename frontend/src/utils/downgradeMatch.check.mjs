// node src/utils/downgradeMatch.check.mjs  —— 纯函数自检
import assert from 'node:assert/strict'
import { templateReference, matchBasis } from './downgradeMatch.js'

const task = { taskFamily: 'OVERSIZE_BAGGAGE_HANDLING' }
const step = (stepSeq, capabilityType) => ({ stepSeq, capabilityType })
const tpl = { templateName: '超规行李处置标准模板', templateIntent: 'OVERSIZE_BAGGAGE_HANDLING', templateVersion: 'V1.3',
  steps: [step(1, 'CAP_BAGGAGE_MEASURE'), step(2, 'CAP_OVERSIZE_ALERT'), step(3, 'CAP_INFO_DISPLAY'), step(4, 'CAP_NAVIGATION')] }
const plan = { source: 'BASELINE_TEMPLATE', baselineTemplateId: 1, snapshotId: 'V1.3', planSteps: tpl.steps }

// 关联入口：模板名称与冻结版本
assert.deepEqual(templateReference(plan, tpl), { templateId: 1, name: '超规行李处置标准模板', version: 'V1.3', currentVersion: 'V1.3' })
// 模板后来被改过：以冻结版本为准，同时给出当前版本
assert.equal(templateReference(plan, { ...tpl, templateVersion: 'V1.5' }).version, 'V1.3')
assert.equal(templateReference(plan, { ...tpl, templateVersion: 'V1.5' }).currentVersion, 'V1.5')
// 取不到模板也不报错，仍给出编号和冻结版本
assert.deepEqual(templateReference(plan, undefined), { templateId: 1, name: null, version: 'V1.3', currentVersion: null })
// 自主计划没有模板关联
assert.equal(templateReference({ source: 'AUTONOMOUS' }, tpl), null)
assert.equal(templateReference(null, tpl), null)

// 三项依据都满足
let rows = matchBasis(task, plan, tpl)
assert.equal(rows.length, 3)
assert.ok(rows.every((r) => r.ok), JSON.stringify(rows))

// 任务族不一致
rows = matchBasis({ taskFamily: 'FLIGHT_CHANGE_RESPONSE' }, plan, tpl)
assert.equal(rows[0].ok, false)

// 计划缺模板里的能力
rows = matchBasis(task, { ...plan, planSteps: [step(1, 'CAP_BAGGAGE_MEASURE')] }, tpl)
assert.equal(rows[1].ok, false)

// 超过五步
rows = matchBasis(task, { ...plan, planSteps: [1, 2, 3, 4, 5, 6].map((n) => step(n, 'CAP_NAVIGATION')) }, tpl)
assert.equal(rows[2].ok, false)
assert.equal(rows[2].actual, '6 步')

// 取不到模板信息：不能显示“通过”
rows = matchBasis(task, plan, undefined)
assert.equal(rows[0].ok, false)
assert.equal(rows[1].ok, false)

// 任务族未指定
assert.equal(matchBasis({}, plan, tpl)[0].ok, false)

// 自主计划不产生匹配依据
assert.deepEqual(matchBasis(task, { source: 'AUTONOMOUS' }, tpl), [])
console.log('downgradeMatch checks passed')
