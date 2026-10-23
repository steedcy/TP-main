<template>
  <div>
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="6"><a-statistic title="设备代理总数" :value="metrics.agentTotal" /></a-col>
      <a-col :span="6"><a-statistic title="在线代理数" :value="metrics.agentOnline" /></a-col>
      <a-col :span="6"><a-statistic title="进行中任务数" :value="metrics.taskInProgress" /></a-col>
      <a-col :span="6"><a-statistic title="未处置异常数" :value="metrics.unhandledExceptions" /></a-col>
    </a-row>

    <a-card title="任务状态分布" style="margin-bottom: 16px">
      <a-row :gutter="16">
        <a-col :span="3" v-for="s in taskStatusList" :key="s.key">
          <a-statistic :title="s.label" :value="metrics.statusCounts[s.key] || 0" @click="goTasks(s.key)" style="cursor: pointer" />
        </a-col>
      </a-row>
    </a-card>

    <a-card title="最新异常列表">
      <a-list :dataSource="latestExceptions" :locale="{ emptyText: '暂无异常' }">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-tag color="orange">{{ item.exceptionType }}</a-tag>
            任务{{ item.taskCode }} - {{ item.detailSummary }} - {{ item.occurredAt }}
          </a-list-item>
        </template>
      </a-list>
    </a-card>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import request from '../../api/request'

const router = useRouter()

// 9种任务状态，对应V1.4正文3.2节任务状态机
const taskStatusList = [
  { key: 'PLANNING', label: '待规划' },
  { key: 'SUPERVISING', label: '监督判定中' },
  { key: 'PENDING_ASSIGNMENT', label: '待分配' },
  { key: 'DOWNGRADING', label: '降级执行中' },
  { key: 'EXECUTING', label: '执行中' },
  { key: 'COMPLETED', label: '已完成' },
  { key: 'FAILED', label: '失败' },
  { key: 'PENDING_MANUAL', label: '待人工处理' },
  { key: 'MANUAL_TERMINATED', label: '人工终止' }
]

const metrics = reactive({
  agentTotal: 0,
  agentOnline: 0,
  taskInProgress: 0,
  unhandledExceptions: 0,
  statusCounts: {}
})
const latestExceptions = ref([])

async function fetchOverview() {
  const resp = await request.get('/dashboard/overview')
  Object.assign(metrics, resp.data.metrics)
  latestExceptions.value = resp.data.latestExceptions
}

function goTasks(status) {
  router.push({ path: '/tasks', query: { status } })
}

let refreshTimer = null
onMounted(() => {
  fetchOverview()
  // 手动刷新为主，此处附加轮询兜底，间隔对齐附录C性能指标（此页面非态势展示，不受5~15秒约束，使用较长周期）
  refreshTimer = setInterval(fetchOverview, 30000)
})

onUnmounted(() => {
  // 退出登录或离开页面后必须清理定时器，否则组件卸载后仍会用已清空的token发请求，
  // 引发401拦截器重复弹窗，且fetchOverview未捕获的rejection会打到控制台
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>
