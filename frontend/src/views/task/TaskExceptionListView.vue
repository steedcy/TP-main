<template>
  <a-space style="margin-bottom: 16px">
    <a-select v-model:value="filterType" placeholder="异常类型" style="width: 180px" allow-clear @change="fetchList">
      <a-select-option value="AGENT_OFFLINE">设备离线</a-select-option>
      <a-select-option value="CAPABILITY_GAP">能力缺口</a-select-option>
      <a-select-option value="EXECUTION_TIMEOUT">执行超时</a-select-option>
      <a-select-option value="STEP_FAILED">步骤失败</a-select-option>
      <a-select-option value="REPLAN_FAILED">重新规划失败</a-select-option>
      <a-select-option value="ASSIGNMENT_FAILED">分配失败</a-select-option>
    </a-select>
    <a-select v-model:value="filterStatus" placeholder="处置状态" style="width: 150px" allow-clear @change="onStatusChange">
      <a-select-option value="PENDING">待处置</a-select-option>
      <a-select-option value="PROCESSING">处置中</a-select-option>
      <a-select-option value="RESOLVED">已处置</a-select-option>
      <a-select-option value="IGNORED">已忽略</a-select-option>
    </a-select>
    <!-- 待处置与历史归档分开看：默认显示全部（TC-058.S2 / DEF-S3-064），可切换待处理/历史归档 -->
    <a-radio-group v-model:value="scope" button-style="solid" @change="onScopeChange" data-testid="exception-scope">
      <a-radio-button value="all">全部（{{ counts.all }}）</a-radio-button>
      <a-radio-button value="active">待处理（{{ counts.active }}）</a-radio-button>
      <a-radio-button value="history">历史归档（{{ counts.history }}）</a-radio-button>
    </a-radio-group>
  </a-space>

  <a-table :dataSource="exceptions" :columns="columns" rowKey="id" size="small">
    <template #bodyCell="{ column, record }">
      <template v-if="column.dataIndex === 'taskId'">
        <router-link :to="`/tasks/${record.taskId}`">任务#{{ record.taskId }}</router-link>
      </template>
      <template v-else-if="column.dataIndex === 'stepSeq'">
        <router-link v-if="record.stepSeq != null" :to="{ path: `/tasks/${record.taskId}`, query: { step: record.stepSeq } }">
          步骤{{ record.stepSeq }}
        </router-link>
        <span v-else>—</span>
      </template>
      <template v-else-if="column.dataIndex === 'reasonCode'">
        <a-tooltip v-if="record.reasonCode" :title="record.reasonCode">
          <span class="reason-code">{{ record.reasonCode }}</span>
        </a-tooltip>
        <span v-else>—</span>
      </template>
      <template v-else-if="column.dataIndex === 'exceptionType'">
        {{ typeLabel(record.exceptionType) }}
      </template>
      <template v-else-if="column.dataIndex === 'exceptionStatus'">
        <a-tag :color="statusColor(record.exceptionStatus)">{{ statusLabel(record.exceptionStatus) }}</a-tag>
      </template>
    </template>
  </a-table>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { listTaskExceptions } from '../../api/task'
import { inScope, scopeCounts, scopeForStatus } from '../../utils/exceptionScope'

const route = useRoute()
const exceptions = ref([])
const filterType = ref(undefined)
const filterStatus = ref(route.query.exceptionStatus || undefined)
// 默认全部（TC-058.S2 / DEF-S3-064）；若路由携带 scope 或 exceptionStatus 查询参数则自动跟随
const scope = ref(route.query.scope || (filterStatus.value ? scopeForStatus(filterStatus.value) : 'all'))
const counts = ref({ active: 0, history: 0, all: 0 })

function onScopeChange() {
  if (filterStatus.value && scope.value !== 'all' && scopeForStatus(filterStatus.value) !== scope.value) {
    filterStatus.value = undefined
  }
  fetchList()
}

function onStatusChange() {
  // 选了具体处置状态就切到对应范围，避免“选了已处置却因范围为待处理而什么都看不到”
  if (filterStatus.value) scope.value = scopeForStatus(filterStatus.value)
  fetchList()
}

const columns = [
  { title: '任务', dataIndex: 'taskId' },
  { title: '步骤', dataIndex: 'stepSeq' },
  { title: '异常类型', dataIndex: 'exceptionType' },
  { title: '原因码', dataIndex: 'reasonCode', width: 220, ellipsis: true },
  { title: '发生时间', dataIndex: 'occurredAt' },
  { title: '首次恢复动作', dataIndex: 'recoveryAction' },
  { title: '恢复结果', dataIndex: 'recoveryResult' },
  { title: '影响判断结论', dataIndex: 'impactConclusion' },
  { title: '处置状态', dataIndex: 'exceptionStatus' }
]

function typeLabel(type) {
  const map = {
    AGENT_OFFLINE: '设备离线', CAPABILITY_GAP: '能力缺口', EXECUTION_TIMEOUT: '执行超时',
    STEP_FAILED: '步骤失败', REPLAN_FAILED: '重新规划失败', ASSIGNMENT_FAILED: '分配失败'
  }
  return map[type] || type
}
function statusLabel(status) {
  const map = { PENDING: '待处置', PROCESSING: '处置中', RESOLVED: '已处置', IGNORED: '已忽略' }
  return map[status] || status
}
function statusColor(status) {
  const map = { PENDING: 'orange', PROCESSING: 'blue', RESOLVED: 'green', IGNORED: 'default' }
  return map[status] || 'default'
}

async function fetchList() {
  const resp = await listTaskExceptions({ exceptionType: filterType.value, exceptionStatus: filterStatus.value })
  const all = resp.data || []
  counts.value = scopeCounts(all)
  exceptions.value = all.filter((r) => inScope(r, scope.value))
}

onMounted(fetchList)
</script>
