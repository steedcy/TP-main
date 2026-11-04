// 风险规则新增/编辑表单的校验（SRS_F013 配置，DEF-S3-042）。规则与后端 RiskRuleController 保持一致：
// 编号必填、不超过64字；内容必填、不超过1000字；首尾空白会被去掉。
export const CODE_MAX = 64
export const CONTENT_MAX = 1000

export function validateRuleForm({ ruleCode, ruleContent }, { editing = false, existingCodes = [] } = {}) {
  const errors = {}
  const code = typeof ruleCode === 'string' ? ruleCode.trim() : ''
  const content = typeof ruleContent === 'string' ? ruleContent.trim() : ''
  if (!editing) {
    if (!code) errors.ruleCode = '请输入规则编号'
    else if (code.length > CODE_MAX) errors.ruleCode = `规则编号不得超过${CODE_MAX}字`
    else if (existingCodes.includes(code)) errors.ruleCode = '规则编号已存在'
  }
  if (!content) errors.ruleContent = '请输入规则内容'
  else if (content.length > CONTENT_MAX) errors.ruleContent = `规则内容不得超过${CONTENT_MAX}字`
  return { ok: Object.keys(errors).length === 0, errors, value: { ruleCode: code, ruleContent: content } }
}
