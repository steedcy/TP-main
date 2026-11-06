// 任务列表的筛选默认值与行样式（SRS_F020.R04、R06，DEF-S3-006、060）。纯函数，不依赖 Vue，便于自检。

// 默认时间范围：当天 00:00:00 到 23:59:59。传入“现在”便于测试；返回 [start, end] 的 Date。
export function todayRange(now = new Date()) {
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0)
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59)
  return [start, end]
}

// 从总览带状态、编号或任务族跳转进来时，不再叠加“今日”，否则会把历史任务过滤掉，看不到总览统计的那批。
export function shouldDefaultToToday(query = {}) {
  return !(query.status || query.taskCode || query.taskFamily || query.goalKeyword)
}

const pad = (n) => String(n).padStart(2, '0')
export function formatLocal(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

// 请求参数：空白关键字不传，时间范围有效才传。
export function buildListParams({ status, taskCode, taskFamily, goalKeyword, range }) {
  const params = {
    status: status || undefined,
    taskCode: taskCode?.trim() || undefined,
    taskFamily: taskFamily || undefined,
    goalKeyword: goalKeyword?.trim() || undefined
  }
  if (Array.isArray(range) && range.length === 2 && range[0] && range[1]) {
    // 范围可以是 Date，也可以是选择器给出的 ISO 字符串
    params.createdFrom = typeof range[0] === 'string' ? range[0] : formatLocal(range[0])
    params.createdTo = typeof range[1] === 'string' ? range[1] : formatLocal(range[1])
  }
  return params
}

// 状态强调：待人工用醒目的橙色，失败用红色，其余不加强调。同时给标签和整行，颜色之外还有文字，不只靠颜色区分。
export function statusTagColor(status) {
  return { PENDING_MANUAL: 'orange', FAILED: 'red', MANUAL_TERMINATED: 'default', EXECUTING: 'blue', DOWNGRADING: 'gold', COMPLETED: 'green' }[status]
}

export function rowClassName(record) {
  return record?.status === 'PENDING_MANUAL' ? 'row-pending-manual' : ''
}
