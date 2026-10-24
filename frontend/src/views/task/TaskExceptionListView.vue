<template>
  <a-space style="margin-bottom: 16px">
    <a-select v-model:value="filterType" placeholder="异常类型" style="width: 180px" allow-clear @change="fetchList">
      <a-select-option value="AGENT_OFFLINE">设备离线</a-select-option>
      <a-select-option value="CAPABILITY_GAP">能力缺口</a-select-option>
      <a-select-option value="EXECUTION_TIMEOUT">执行超时</a-select-option>
      <a-select-option value="STEP_FAILED">步骤失败</a-select-option>
      <a-select-option value="REPLAN_FAILED">重新规划失败</a-select-option>
    </a-select>
    <a-select v-model:value="filterStatus" placeholder="处置状态" style="width: 150px" allow-clear @change="fetchList">
      <a-select-option value="PENDING">待处置</a-select-option>
      <a-select-option value="PROCESSING">处置中</a-select-option>
      <a-select-option value="RESOLVED">已处置</a-select-option>
      <a-select-option value="IGNORED">已忽略</a-select-option>
    </a-select>
  </a-space>

  <a-table :dataSource="exceptions" :columns="columns" rowKey="id" size="small">
    <template #bodyCell="{ column, record }">
      <template v-if="column.dataIndex === 'taskId'">
        <router-link :to="`/tasks/${record.taskId}`">任务#{{ record.taskId }}</router-link>
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

const exceptions = ref([])
const filterType = ref(undefined)
const filterStatus = ref(useRoute().query.exceptionStatus || undefined)

const columns = [
  { title: '任务', dataIndex: 'taskId' },
  { title: '步骤', dataIndex: 'stepSeq' },
  { title: '异常类型', dataIndex: 'exceptionType' },
  { title: '发生时间', dataIndex: 'occurredAt' },
  { title: '首次恢复动作', dataIndex: 'recoveryAction' },
  { title: '恢复结果', dataIndex: 'recoveryResult' },
  { title: '影响判断结论', dataIndex: 'impactConclusion' },
  { title: '处置状态', dataIndex: 'exceptionStatus' }
]

function typeLabel(type) {
  const map = {
    AGENT_OFFLINE: '设备离线', CAPABILITY_GAP: '能力缺口', EXECUTION_TIMEOUT: '执行超时',
    STEP_FAILED: '步骤失败', REPLAN_FAILED: '重新规划失败'
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
  exceptions.value = resp.data
}

onMounted(fetchList)
</script>
