// 异常列表的“待处理 / 历史归档”划分（SRS_F018.R09、R10，DEF-S3-064）。
// 待处理 = 还需要人关注或系统仍在处置：PENDING、PROCESSING。
// 历史归档 = 已有结论：RESOLVED、IGNORED。未知状态按待处理，避免异常被悄悄归档。
export const ACTIVE_STATUSES = ['PENDING', 'PROCESSING']
export const HISTORY_STATUSES = ['RESOLVED', 'IGNORED']

export function inScope(record, scope) {
  if (scope === 'all') return true
  const archived = HISTORY_STATUSES.includes(record?.exceptionStatus)
  return scope === 'history' ? archived : !archived
}

export function scopeCounts(records) {
  const list = Array.isArray(records) ? records : []
  const history = list.filter((r) => inScope(r, 'history')).length
  return { active: list.length - history, history, all: list.length }
}

// 总览跳转带 exceptionStatus 时，范围跟着状态走，保证跳转后看到的就是点击的那类异常
export function scopeForStatus(status) {
  if (!status) return 'active'
  return HISTORY_STATUSES.includes(status) ? 'history' : 'active'
}
