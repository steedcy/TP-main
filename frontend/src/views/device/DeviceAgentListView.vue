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

    <a-space v-if="isConfigAdmin" style="margin-left: 16px">
      <span>心跳超时阈值（秒，10~120）：</span>
      <a-input-number v-model:value="heartbeatSeconds" :min="10" :max="120" />
      <a-button type="primary" @click="saveHeartbeat">保存</a-button>
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
          <template v-if="record.currentTaskId">
            <router-link v-if="canOpenTask" :to="`/tasks/${record.currentTaskId}`">
              任务#{{ record.currentTaskId }}（步骤{{ record.currentStepSeq }}）
            </router-link>
            <span v-else>任务#{{ record.currentTaskId }}（步骤{{ record.currentStepSeq }}）</span>
          </template>
          <span v-else>—</span>
        </template>
        <template v-else-if="column.key === 'lastReportedAt'">
          <a-tooltip v-if="record.offlineInfo">
            <template #title>
              <div>代理：{{ record.offlineInfo.agentCode }}</div>
              <div>离线时间：{{ record.offlineInfo.offlineAt || '—' }}</div>
              <div>原因码：{{ record.offlineInfo.reasonCode || '—' }}</div>
              <div>{{ record.offlineInfo.affectsTask ? '影响进行中任务，已进入恢复判断' : '未占用任务，不影响任务' }}</div>
            </template>
            <span class="offline-time">{{ record.lastReportedAt || '—' }}</span>
          </a-tooltip>
          <span v-else>{{ record.lastReportedAt || '—' }}</span>
        </template>
        <template v-else-if="column.key === 'capabilities'">
          <a-tag v-for="c in record.enabledCapabilities" :key="c.capabilityCode">{{ c.capabilityCode }} {{ c.capabilityName }}</a-tag>
          <span v-if="!record.enabledCapabilities?.length">—</span>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button size="small" style="margin-right: 8px" @click="openDetail(record)">详情</a-button>
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

    <a-drawer :open="!!detail" title="设备代理详情" width="480" @close="detail = null">
      <a-descriptions v-if="detail" bordered :column="1" size="small">
        <a-descriptions-item label="代理编号">{{ detail.agentId }}</a-descriptions-item>
        <a-descriptions-item label="设备">{{ detail.deviceName }}（{{ detail.deviceCode }}）</a-descriptions-item>
        <a-descriptions-item label="代理状态">{{ { ENABLED: '启用', DISABLED: '停用', ARCHIVED: '归档' }[detail.agentStatus] }}</a-descriptions-item>
        <a-descriptions-item label="在线状态">{{ detail.onlineStatus === 'ONLINE' ? '在线' : '离线' }}</a-descriptions-item>
        <a-descriptions-item label="工作状态">{{ detail.workStatus === 'BUSY' ? '占用' : '空闲' }}</a-descriptions-item>
        <a-descriptions-item label="当前任务">
          <template v-if="detail.currentTaskId">任务#{{ detail.currentTaskId }}（步骤{{ detail.currentStepSeq }}）</template>
          <template v-else>—</template>
        </a-descriptions-item>
        <a-descriptions-item label="最后上报时间">{{ detail.lastReportedAt || '—' }}</a-descriptions-item>
        <a-descriptions-item v-if="detail.offlineInfo" label="离线信息">
          <div>离线时间：{{ detail.offlineInfo.offlineAt || '—' }}</div>
          <div>原因码：{{ detail.offlineInfo.reasonCode || '—' }}</div>
          <div>{{ detail.offlineInfo.affectsTask ? '影响进行中任务' : '不影响任务' }}</div>
        </a-descriptions-item>
        <a-descriptions-item label="启用能力">
          <div v-for="c in detail.enabledCapabilities" :key="c.capabilityCode">{{ c.capabilityCode }}　{{ c.capabilityName }}</div>
          <span v-if="!detail.enabledCapabilities?.length">无已启用能力</span>
        </a-descriptions-item>
      </a-descriptions>
      <a-divider>消息与事件时间线</a-divider>
      <a-table :dataSource="timeline" :pagination="{ pageSize: 10 }" size="small" rowKey="rowKey"
        :columns="[{ title: '时间', dataIndex: 'at', width: 170 }, { title: '类型', dataIndex: 'type' },
                   { title: '指令号', dataIndex: 'commandId' }, { title: '摘要', dataIndex: 'summary' },
                   { title: '结果', key: 'result', customRender: ({ record }) => timelineResult(record) },
                   { title: '原因码', key: 'reasonCode', customRender: ({ record }) => timelineReason(record) }]" />
    </a-drawer>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { listAgents, disableAgent, getHeartbeatTimeout, updateHeartbeatTimeout, getAgentTimeline } from '../../api/device'
import { timelineResult, timelineReason } from '../../utils/timeline'
import { useAuthStore } from '../../store/auth'

const list = ref([])
const detail = ref(null)
const timeline = ref([])
async function openDetail(record) {
  detail.value = record
  timeline.value = []
  const resp = await getAgentTimeline(record.agentId)
  timeline.value = resp.data.map((t, i) => ({ ...t, rowKey: i }))
}
const auth = useAuthStore()
// 配置管理员无权读取任务详情，当前任务只显示文本，不提供链接
const canOpenTask = auth.role === 'OPERATOR' || auth.role === 'SYSTEM_ADMIN'
const isConfigAdmin = auth.role === 'CONFIG_ADMIN'
const heartbeatSeconds = ref(30)
const route = useRoute()
const filters = reactive({ agentStatus: route.query.agentStatus || undefined, onlineStatus: route.query.onlineStatus || undefined })
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const columns = [
  { title: '代理编号', dataIndex: 'agentId' },
  { title: '关联设备', dataIndex: 'deviceName' },
  { title: '设备编码', dataIndex: 'deviceCode' },
  { title: '代理状态', key: 'agentStatus' },
  { title: '在线状态', key: 'onlineStatus' },
  { title: '工作状态', key: 'workStatus' },
  { title: '当前任务', key: 'currentTask' },
  { title: '启用能力', key: 'capabilities' },
  { title: '最后上报时间', key: 'lastReportedAt' },
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

async function saveHeartbeat() {
  await updateHeartbeatTimeout(heartbeatSeconds.value)
  message.success('心跳超时阈值已更新，后续离线判断按新阈值生效')
}

onMounted(async () => {
  fetchList()
  try { heartbeatSeconds.value = (await getHeartbeatTimeout()).data.seconds } catch { /* 无权限时不显示 */ }
})
</script>

<style scoped>
.offline-time { color: #cf1322; font-weight: 600; }
</style>
