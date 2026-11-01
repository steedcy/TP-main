// 任务执行进度（SRS_F017.R01，DEF-S3-068）：完成数/总数，以及当前正在处理的步骤。
// 总数取当前计划版本的步骤数；被冻结或条件分支跳过的步骤仍计入总数，但不算已完成。
// 分配记录缺失的步骤（尚未分配）按“待分配”处理，所以总数不会因记录还没生成而偏小。

const ACTIVE = ['EXECUTING', 'PENDING_ASSIGNMENT']

export function taskProgress(planSteps, assignments) {
  const steps = Array.isArray(planSteps) ? planSteps : []
  const rows = Array.isArray(assignments) ? assignments : []
  const bySeq = new Map(rows.map((a) => [a.stepSeq, a]))
  const total = steps.length || rows.length
  const seqs = steps.length ? steps.map((s) => s.stepSeq) : rows.map((a) => a.stepSeq)
  const statusOf = (seq) => bySeq.get(seq)?.stepStatus || 'PENDING_ASSIGNMENT'
  const completed = seqs.filter((seq) => statusOf(seq) === 'COMPLETED').length
  const skipped = seqs.filter((seq) => statusOf(seq) === 'SKIPPED').length
  const failed = seqs.filter((seq) => statusOf(seq) === 'FAILED').length
  const current = [...seqs].sort((a, b) => a - b).find((seq) => ACTIVE.includes(statusOf(seq))) ?? null
  return { total, completed, skipped, failed, current, percent: total ? Math.round((completed / total) * 100) : 0 }
}

export function progressText(progress) {
  if (!progress || !progress.total) return '—'
  const extra = []
  if (progress.skipped) extra.push(`跳过${progress.skipped}`)
  if (progress.failed) extra.push(`失败${progress.failed}`)
  const now = progress.current != null ? `，当前步骤${progress.current}` : ''
  return `${progress.completed}/${progress.total}${extra.length ? '（' + extra.join('，') + '）' : ''}${now}`
}
