// node src/utils/riskRuleForm.check.mjs
import assert from 'node:assert/strict'
import { validateRuleForm, CODE_MAX, CONTENT_MAX } from './riskRuleForm.js'

let r = validateRuleForm({ ruleCode: '  R-NEW ', ruleContent: ' 内容 ' })
assert.equal(r.ok, true)
assert.deepEqual(r.value, { ruleCode: 'R-NEW', ruleContent: '内容' })

for (const bad of [undefined, null, '', '   ', 123]) {
  assert.equal(validateRuleForm({ ruleCode: bad, ruleContent: '内容' }).errors.ruleCode, '请输入规则编号', String(bad))
  assert.equal(validateRuleForm({ ruleCode: 'R1', ruleContent: bad }).errors.ruleContent, '请输入规则内容', String(bad))
}
assert.equal(validateRuleForm({ ruleCode: 'x'.repeat(CODE_MAX + 1), ruleContent: 'a' }).errors.ruleCode, `规则编号不得超过${CODE_MAX}字`)
assert.equal(validateRuleForm({ ruleCode: 'x'.repeat(CODE_MAX), ruleContent: 'a' }).ok, true)
assert.equal(validateRuleForm({ ruleCode: 'R1', ruleContent: 'x'.repeat(CONTENT_MAX + 1) }).errors.ruleContent, `规则内容不得超过${CONTENT_MAX}字`)

// 重复编号只在新增时检查，且比较的是去空白后的值
assert.equal(validateRuleForm({ ruleCode: ' R1 ', ruleContent: 'a' }, { existingCodes: ['R1'] }).errors.ruleCode, '规则编号已存在')
// 编辑时不校验编号（编号不可改），只校验内容
r = validateRuleForm({ ruleCode: '', ruleContent: '新内容' }, { editing: true, existingCodes: ['R1'] })
assert.equal(r.ok, true)
assert.equal(validateRuleForm({ ruleCode: 'R1', ruleContent: ' ' }, { editing: true }).errors.ruleContent, '请输入规则内容')
console.log('riskRuleForm checks passed')
