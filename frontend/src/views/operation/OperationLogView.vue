<template>
  <div>
    <a-space style="margin-bottom: 16px" wrap>
      <a-input v-model:value="filters.username" placeholder="操作账号" style="width: 140px" @pressEnter="fetchList" />
      <a-select v-model:value="filters.operationType" placeholder="操作类型" allow-clear style="width: 200px" @change="fetchList">
        <a-select-option v-for="opt in operationTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</a-select-option>
      </a-select>
      <a-select v-model:value="filters.operationResult" placeholder="操作结果" allow-clear style="width: 120px" @change="fetchList">
        <a-select-option value="SUCCESS">成功</a-select-option>
        <a-select-option value="FAILED">失败</a-select-option>
      </a-select>
      <a-range-picker v-model:value="timeRange" show-time format="YYYY-MM-DD HH:mm:ss" @change="fetchList" />
      <a-button type="primary" @click="fetchList">查询</a-button>
    </a-space>

    <a-table :dataSource="list" :columns="columns" rowKey="id" :pagination="pagination" @change="handleTableChange">
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'operationType'">
          {{ typeLabel(record.operationType) }}
        </template>
        <template v-else-if="column.dataIndex === 'operationResult'">
          <a-tag :color="record.operationResult === 'SUCCESS' ? 'green' : 'red'">
            {{ record.operationResult === 'SUCCESS' ? '成功' : '失败' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a @click="openDetail(record)">详情</a>
        </template>
      </template>
    </a-table>

    <!-- 对应5.7.2界面元素"详情"：变更前后关键字段摘要，凭据类字段已由后端掩码，不提供原值查看入口 -->
    <a-modal v-model:open="detailVisible" title="操作详情" :footer="null">
      <a-descriptions bordered :column="1" size="small" v-if="detailRecord">
        <a-descriptions-item label="操作时间">{{ detailRecord.createdAt }}</a-descriptions-item>
        <a-descriptions-item label="操作人">{{ detailRecord.username }}（{{ detailRecord.role }}）</a-descriptions-item>
        <a-descriptions-item label="操作类型">{{ typeLabel(detailRecord.operationType) }}</a-descriptions-item>
        <a-descriptions-item label="操作对象">{{ detailRecord.operationTarget || '—' }}</a-descriptions-item>
        <a-descriptions-item label="来源IP">{{ detailRecord.sourceIp || '—' }}</a-descriptions-item>
      </a-descriptions>
      <p style="margin-top: 12px"><b>变更前后关键字段摘要：</b></p>
      <pre v-if="parsedDetail">{{ JSON.stringify(parsedDetail, null, 2) }}</pre>
      <a-empty v-else description="本条记录未附带详情" />
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { listOperationLogs } from '../../api/operation'

const list = ref([])
const filters = reactive({ username: '', operationType: undefined, operationResult: undefined })
// 对应5.7.2界面元素"时间范围"默认值：近7日
const timeRange = ref([dayjs().subtract(7, 'day').startOf('day'), dayjs().endOf('day')])
const pagination = reactive({ current: 1, pageSize: 20, total: 0, showSizeChanger: true })
const detailVisible = ref(false)
const detailRecord = ref(null)

// 对应5.7.2界面元素"操作类型"下拉：登录、退出、设备配置、能力启停、模板启停、
// 任务定义变更、风险规则变更、人工终止、人工处置，映射到后端实际写入的operationType值
const operationTypeOptions = [
  { value: 'LOGIN', label: '登录' },
  { value: 'LOGOUT', label: '退出' },
  { value: 'ACCESS_DENIED', label: '越权访问' },
  { value: 'DEVICE_CREATE', label: '设备配置-新增' },
  { value: 'DEVICE_UPDATE', label: '设备配置-修改' },
  { value: 'DEVICE_DELETE', label: '设备配置-删除' },
  { value: 'DEVICE_CONNECTION_TEST', label: '设备配置-连接测试' },
  { value: 'DEVICE_STATUS_CHANGE', label: '设备配置-启停' },
  { value: 'DEVICE_AGENT_CREATE', label: '设备代理-创建' },
  { value: 'DEVICE_AGENT_DISABLE', label: '设备代理-停用' },
  { value: 'DEVICE_CAPABILITY_CREATE', label: '能力-新增' },
  { value: 'DEVICE_CAPABILITY_UPDATE', label: '能力-修改' },
  { value: 'DEVICE_CAPABILITY_TEST', label: '能力-测试' },
  { value: 'DEVICE_CAPABILITY_STATUS_CHANGE', label: '能力启停' },
  { value: 'CAP_TEMPLATE_STATUS_CHANGE', label: '能力模板启停' },
  { value: 'DEVICE_TYPE_BOUNDARY_UPDATE', label: '能力边界配置变更' },
  { value: 'BASELINE_TEMPLATE_CREATE', label: '基线模板-新增' },
  { value: 'BASELINE_TEMPLATE_UPDATE', label: '基线模板-修改' },
  { value: 'BASELINE_TEMPLATE_ENABLE', label: '模板启用' },
  { value: 'BASELINE_TEMPLATE_DISABLE', label: '模板停用' },
  { value: 'BASELINE_TEMPLATE_DELETE', label: '基线模板-删除' },
  { value: 'BASELINE_TEMPLATE_DRY_RUN', label: '基线模板-试运行' },
  { value: 'RISK_RULE_CHANGE', label: '风险规则变更' },
  { value: 'TASK_SUBMIT', label: '任务提交' },
  { value: 'TASK_CANCEL', label: '任务取消' },
  { value: 'TASK_TERMINATE', label: '人工终止' },
  { value: 'TASK_MANUAL_ACTION', label: '人工处置' },
  { value: 'MANUAL_HANDLING', label: '账号解锁（人工处置）' },
  { value: 'USER_CREATE', label: '账号创建' },
  { value: 'PASSWORD_RESET', label: '密码重置' },
  { value: 'USER_STATUS_CHANGE', label: '账号启停' }
]

const columns = [
  { title: '操作时间', dataIndex: 'createdAt' },
  { title: '操作账号', dataIndex: 'username' },
  { title: '角色', dataIndex: 'role' },
  { title: '操作类型', dataIndex: 'operationType' },
  { title: '操作对象', dataIndex: 'operationTarget' },
  { title: '结果', dataIndex: 'operationResult' },
  { title: '来源IP', dataIndex: 'sourceIp' },
  { title: '操作', key: 'action' }
]

function typeLabel(type) {
  return operationTypeOptions.find((o) => o.value === type)?.label || type
}

const parsedDetail = computed(() => {
  if (!detailRecord.value?.detail) return null
  try {
    return JSON.parse(detailRecord.value.detail)
  } catch {
    return null
  }
})

function openDetail(record) {
  detailRecord.value = record
  detailVisible.value = true
}

async function fetchList() {
  const params = {
    username: filters.username,
    operationType: filters.operationType,
    operationResult: filters.operationResult,
    page: pagination.current,
    size: pagination.pageSize
  }
  if (timeRange.value?.length === 2) {
    params.startTime = timeRange.value[0].format('YYYY-MM-DDTHH:mm:ss')
    params.endTime = timeRange.value[1].format('YYYY-MM-DDTHH:mm:ss')
  }
  const resp = await listOperationLogs(params)
  list.value = resp.data.content || resp.data
  pagination.total = resp.data.totalElements || 0
}

function handleTableChange(pag) {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchList()
}

onMounted(fetchList)
</script>
