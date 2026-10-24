<template>
  <div>
    <a-space style="margin-bottom: 16px">
      <a-select v-model:value="period" style="width: 140px" @change="fetchOverview">
        <a-select-option value="TODAY">今日</a-select-option>
        <a-select-option value="LAST_7_DAYS">近7日</a-select-option>
      </a-select>
      <a-button :loading="loading" @click="fetchOverview">刷新</a-button>
      <span v-if="lastRefreshedAt">更新于 {{ lastRefreshedAt }}</span>
    </a-space>
    <a-alert v-if="loadFailed" type="error" show-icon message="总览加载失败，请重试" style="margin-bottom: 16px" />

    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="isTaskViewer ? 4 : 12"><a-card hoverable @click="goAgents()"><a-statistic title="设备代理总数" :value="display(metrics.agentTotal)" /></a-card></a-col>
      <a-col :span="isTaskViewer ? 4 : 12"><a-card hoverable @click="goAgents('ONLINE')"><a-statistic title="在线代理数" :value="display(metrics.agentOnline)" /></a-card></a-col>
      <template v-if="isTaskViewer">
        <a-col :span="4"><a-card hoverable @click="goTasks()"><a-statistic title="进行中任务数" :value="display(metrics.taskInProgress)" /></a-card></a-col>
        <a-col :span="4"><a-card><a-statistic title="重新规划次数" :value="display(metrics.replanningCount)" /></a-card></a-col>
        <a-col :span="4"><a-card hoverable @click="goExceptions"><a-statistic title="未处置异常数" :value="display(metrics.unhandledExceptions)" /></a-card></a-col>
        <a-col :span="4"><a-card hoverable @click="goTasks('PENDING_MANUAL')" :style="metrics.pendingManual ? 'border-color: #fa8c16' : ''"><a-statistic title="待人工任务数" :value="display(metrics.pendingManual)" /></a-card></a-col>
      </template>
    </a-row>

    <template v-if="isTaskViewer">
      <a-card title="任务状态分布" style="margin-bottom: 16px">
        <a-row :gutter="16">
          <a-col :span="8" v-for="s in taskStatusList" :key="s.key" style="margin-bottom: 8px">
            <a-card size="small" hoverable @click="goTasks(s.key)" :style="s.key === 'PENDING_MANUAL' && metrics.statusCounts?.[s.key] ? 'border-color: #fa8c16' : ''">
              <a-statistic :title="s.label" :value="display(metrics.statusCounts?.[s.key])" />
            </a-card>
          </a-col>
        </a-row>
      </a-card>

      <a-card title="最新异常列表">
        <a-list :dataSource="latestExceptions" :locale="{ emptyText: '暂无异常' }">
          <template #renderItem="{ item }">
            <a-list-item style="cursor: pointer" @click="selectedException = item">
              <a-tag color="orange">{{ item.exceptionType }}</a-tag>
              任务{{ item.taskCode }} · {{ item.exceptionStatus }} · {{ item.occurredAt }}
            </a-list-item>
          </template>
        </a-list>
      </a-card>
      <a-modal :open="!!selectedException" title="异常详情" :footer="null" @cancel="selectedException = null">
        <a-descriptions v-if="selectedException" bordered :column="1">
          <a-descriptions-item label="任务"><router-link :to="`/tasks/${selectedException.taskId}`">{{ selectedException.taskCode }}</router-link></a-descriptions-item>
          <a-descriptions-item label="异常类型">{{ selectedException.exceptionType }}</a-descriptions-item>
          <a-descriptions-item label="发生时间">{{ selectedException.occurredAt }}</a-descriptions-item>
          <a-descriptions-item label="处置状态">{{ selectedException.exceptionStatus }}</a-descriptions-item>
          <a-descriptions-item label="原因码">{{ selectedException.reasonCode || '—' }}</a-descriptions-item>
          <a-descriptions-item label="影响判断">{{ selectedException.impactConclusion || '—' }}</a-descriptions-item>
        </a-descriptions>
      </a-modal>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../store/auth'
import request from '../../api/request'

const router = useRouter()
const auth = useAuthStore()
const isTaskViewer = computed(() => auth.role === 'OPERATOR' || auth.role === 'SYSTEM_ADMIN')
const period = ref('TODAY')
const loading = ref(false)
const loadFailed = ref(false)
const lastRefreshedAt = ref('')
const metrics = reactive({ agentTotal: null, agentOnline: null, taskInProgress: null,
  unhandledExceptions: null, pendingManual: null, replanningCount: null, statusCounts: {} })
const latestExceptions = ref([])
const selectedException = ref(null)
const taskStatusList = [
  { key: 'PLANNING', label: '待规划' }, { key: 'SUPERVISING', label: '监督判定中' },
  { key: 'PENDING_ASSIGNMENT', label: '待分配' }, { key: 'DOWNGRADING', label: '降级执行中' },
  { key: 'EXECUTING', label: '执行中' }, { key: 'COMPLETED', label: '已完成' },
  { key: 'FAILED', label: '失败' }, { key: 'PENDING_MANUAL', label: '待人工处理' },
  { key: 'MANUAL_TERMINATED', label: '人工终止' }
]

function display(value) { return value == null ? '--' : value }
async function fetchOverview() {
  loading.value = true
  loadFailed.value = false
  try {
    const resp = await request.get('/dashboard/overview', { params: { period: period.value }, silent: true })
    Object.assign(metrics, resp.data.metrics)
    latestExceptions.value = resp.data.latestExceptions || []
    lastRefreshedAt.value = new Date().toLocaleTimeString('zh-CN')
  } catch {
    loadFailed.value = true
    for (const key of ['agentTotal', 'agentOnline', 'taskInProgress', 'unhandledExceptions', 'pendingManual', 'replanningCount']) metrics[key] = null
    metrics.statusCounts = Object.fromEntries(taskStatusList.map(s => [s.key, null]))
    latestExceptions.value = []
  } finally { loading.value = false }
}
function goAgents(onlineStatus) { router.push({ path: '/device-agents', query: onlineStatus ? { onlineStatus } : {} }) }
function goTasks(status) { router.push({ path: '/tasks', query: status ? { status } : {} }) }
function goExceptions() { router.push({ path: '/task-exceptions', query: { exceptionStatus: 'PENDING' } }) }

let refreshTimer = null
onMounted(() => { fetchOverview(); refreshTimer = setInterval(fetchOverview, 30000) })
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })
</script>
