// 自主候选计划详情的汇总字段（SRS_F012，DEF-S3-036）：可执行步骤数、剩余额度、每步参数。
// 任务总步骤上限为 5（与后端 PlanValidationService 一致）。

export const TOTAL_STEP_QUOTA = 5

export function stepCount(planVersion) {
  return Array.isArray(planVersion?.planSteps) ? planVersion.planSteps.length : 0
}

// 剩余额度 = 总上限 - 当前版本已有的步骤数，不为负。超限的版本（校验会拒绝）显示 0 并标出超出几步。
export function quotaSummary(planVersion) {
  const used = stepCount(planVersion)
  const remaining = Math.max(0, TOTAL_STEP_QUOTA - used)
  return { used, total: TOTAL_STEP_QUOTA, remaining, exceededBy: Math.max(0, used - TOTAL_STEP_QUOTA) }
}

export function quotaText(planVersion) {
  const q = quotaSummary(planVersion)
  const base = `${q.used} 步 / 上限 ${q.total} 步，剩余额度 ${q.remaining} 步`
  return q.exceededBy > 0 ? `${base}（超出 ${q.exceededBy} 步）` : base
}

// 把 inputParams 展开成可读的“名称=值”文本；值可能是对象或数组，序列化后截断，避免撑破表格。
export function formatInputParams(inputParams, maxLength = 160) {
  if (inputParams == null || typeof inputParams !== 'object' || Array.isArray(inputParams)) return '—'
  const entries = Object.entries(inputParams)
  if (!entries.length) return '—'
  const text = entries.map(([k, v]) => `${k}=${typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v)}`).join('；')
  return text.length > maxLength ? text.slice(0, maxLength) + '…' : text
}

// 参数来源：模板输入引用（TEMPLATE_INPUT.x / STEPn_OUTPUT.x）或场景参数，缺失时说明是模型直接给的字面量。
export function paramSourceText(step, sceneParams = {}) {
  const params = step?.inputParams
  if (!params || typeof params !== 'object') return '—'
  const sources = new Set()
  for (const [name, value] of Object.entries(params)) {
    if (typeof value === 'string' && /^(TEMPLATE_INPUT|STEP\d+_OUTPUT)\./.test(value)) sources.add(value.split('.')[0])
    else if (sceneParams && Object.prototype.hasOwnProperty.call(sceneParams, name)) sources.add('场景参数')
    else sources.add('规划给出')
  }
  return [...sources].join('、') || '—'
}
