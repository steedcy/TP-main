// 基线降级详情：计划版本与所用模板的关联，以及“为什么选这个模板”的逐项匹配依据
// （SRS_F015.R06，DEF-S3-067）。三项依据：任务族/目标、所需能力、五步限制。
// 只用页面已有的数据：任务（taskFamily）、计划版本（baselineTemplateId、snapshotId、planSteps）、模板详情。

export const MAX_STEPS = 5

export function templateReference(planVersion, template) {
  if (!planVersion || planVersion.source !== 'BASELINE_TEMPLATE') return null
  return {
    templateId: planVersion.baselineTemplateId ?? null,
    name: template?.templateName ?? null,
    // 计划冻结时记录的模板版本；模板之后被改过也以冻结值为准
    version: planVersion.snapshotId ?? template?.templateVersion ?? null,
    currentVersion: template?.templateVersion ?? null
  }
}

export function matchBasis(task, planVersion, template) {
  if (!planVersion || planVersion.source !== 'BASELINE_TEMPLATE') return []
  const steps = Array.isArray(planVersion.planSteps) ? planVersion.planSteps : []
  const rows = []

  const family = task?.taskFamily || null
  const intent = template?.templateIntent || null
  rows.push({
    item: '任务族 / 模板意图',
    expected: family || '未指定',
    actual: intent || '未取得模板信息',
    ok: !!family && !!intent && family === intent
  })

  const templateCaps = Array.isArray(template?.steps) ? template.steps.map((s) => s.capabilityType) : []
  const planCaps = steps.map((s) => s.capabilityType)
  const missing = templateCaps.filter((c) => !planCaps.includes(c))
  rows.push({
    item: '所需能力',
    expected: templateCaps.length ? [...new Set(templateCaps)].join('、') : '未取得模板信息',
    actual: planCaps.length ? [...new Set(planCaps)].join('、') : '计划无步骤',
    ok: templateCaps.length > 0 && missing.length === 0
  })

  rows.push({
    item: '步骤数上限',
    expected: `≤ ${MAX_STEPS} 步`,
    actual: `${steps.length} 步`,
    ok: steps.length > 0 && steps.length <= MAX_STEPS
  })
  return rows
}
