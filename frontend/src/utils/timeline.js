// 代理消息时间线的结果与原因码展示（SRS_F007.R06、R07，DEF-S3-084）：
// 结果和原因码是两项信息，同时显示，不能让结果遮住原因码；都没有时显示占位符。
export const EMPTY_CELL = '—'

export function timelineResult(record) {
  return record?.result || EMPTY_CELL
}

export function timelineReason(record) {
  return record?.reasonCode || EMPTY_CELL
}

// 供提示或导出使用：同时有结果和原因码时合并成一句
export function timelineOutcome(record) {
  const result = record?.result
  const reason = record?.reasonCode
  if (result && reason) return `${result}（${reason}）`
  return result || reason || EMPTY_CELL
}
