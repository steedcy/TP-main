<template>
  <div>
    <a-space style="margin-bottom: 16px">
      <a-select v-model:value="filters.agentStatus" style="width: 140px" placeholder="代理状态" allow-clear @change="fetchList">
        <a-select-option value="ENABLED">启用</a-select-option>
        <a-select-option value="DISABLED">停用</a-select-option>
        <a-select-option value="ARCHIVED">归档</a-select-option>
      </a-select>
      <a-select v-model:value="filters.onlineStatus" style="width: 140px" placeholder="在线状态" allow-clear @change="fetchList">
        <a-select-option value="ONLINE">在线</a-select-option>
        <a-select-option value="OFFLINE">离线</a-select-option>
      </a-select>
    </a-space>

    <a-table :dataSource="list" :columns="columns" rowKey="agentId" :pagination="pagination" @change="handleTableChange">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'onlineStatus'">
          <a-badge :status="record.onlineStatus === 'ONLINE' ? 'success' : 'default'" :text="record.onlineStatus === 'ONLINE' ? '在线' : '离线'" />
        </template>
        <template v-else-if="column.key === 'workStatus'">
          <a-tag :color="record.workStatus === 'BUSY' ? 'orange' : 'default'">{{ record.workStatus === 'BUSY' ? '占用' : '空闲' }}</a-tag>
        </template>
        <template v-else-if="column.key === 'agentStatus'">
          <a-tag :color="{ ENABLED: 'green', DISABLED: 'default', ARCHIVED: 'red' }[record.agentStatus]">
            {{ { ENABLED: '启用', DISABLED: '停用', ARCHIVED: '归档' }[record.agentStatus] }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'currentTask'">
          <router-link v-if="record.currentTaskId" :to="`/tasks/${record.currentTaskId}`">
            任务#{{ record.currentTaskId }}（步骤{{ record.currentStepSeq }}）
          </router-link>
          <span v-else>—</span>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-popconfirm
            v-if="record.agentStatus === 'ENABLED'"
            title="停用后代理立即退出可用候选集合，确认停用？"
            @confirm="handleDisable(record)"
          >
            <a-button size="small" danger>停用</a-button>
          </a-popconfirm>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { listAgents, disableAgent } from '../../api/device'

const list = ref([])
const filters = reactive({ agentStatus: undefined, onlineStatus: undefined })
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const columns = [
  { title: '代理编号', dataIndex: 'agentId' },
  { title: '关联设备', dataIndex: 'deviceName' },
  { title: '设备编码', dataIndex: 'deviceCode' },
  { title: '代理状态', key: 'agentStatus' },
  { title: '在线状态', key: 'onlineStatus' },
  { title: '工作状态', key: 'workStatus' },
  { title: '当前任务', key: 'currentTask' },
  { title: '最后上报时间', dataIndex: 'lastReportedAt' },
  { title: '操作', key: 'action' }
]

async function fetchList() {
  const resp = await listAgents({
    agentStatus: filters.agentStatus, onlineStatus: filters.onlineStatus,
    page: pagination.current, size: pagination.pageSize
  })
  list.value = resp.data.content
  pagination.total = resp.data.totalElements
}

function handleTableChange(pag) {
  pagination.current = pag.current
  fetchList()
}

async function handleDisable(record) {
  await disableAgent(record.agentId)
  message.success('设备代理已停用')
  fetchList()
}

onMounted(fetchList)
</script>
