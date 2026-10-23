<template>
  <a-row :gutter="16">
    <a-col :span="9">
      <!-- 对应5.7.1界面元素：任务编号、时间范围、任务族/状态筛选 -->
      <a-space direction="vertical" style="width: 100%; margin-bottom: 12px">
        <a-input v-model:value="filters.taskCode" placeholder="任务编号（精确）" @pressEnter="fetchList" />
        <a-range-picker v-model:value="timeRange" show-time format="YYYY-MM-DD HH:mm:ss" style="width: 100%" @change="fetchList" />
        <a-select v-model:value="filters.taskFamily" placeholder="任务族" allow-clear style="width: 100%" @change="fetchList">
          <a-select-option v-for="d in taskDefinitions" :key="d.definitionCode" :value="d.definitionCode">{{ d.taskName }}</a-select-option>
        </a-select>
        <a-select v-model:value="filters.status" placeholder="任务状态" allow-clear style="width: 100%" @change="fetchList">
          <a-select-option v-for="s in statusOptions" :key="s.key" :value="s.key">{{ s.label }}</a-select-option>
        </a-select>
        <a-button type="primary" block @click="fetchList">查询</a-button>
      </a-space>

      <!-- 异常路径2a：查询条件命中记录为空，展示空态提示 -->
      <a-empty v-if="!taskList.length" description="未查询到符合条件的任务" />
      <a-list v-else :dataSource="taskList" size="small" :bordered="true" style="max-height: 640px; overflow-y: auto">
        <template #renderItem="{ item }">
          <a-list-item :class="{ 'selected-item': item.id === selectedTaskId }" style="cursor: pointer" @click="selectTask(item)">
            <a-list-item-meta :description="item.taskGoal">
              <template #title>{{ item.taskCode }} · {{ statusLabel(item.status) }}</template>
            </a-list-item-meta>
            <span>{{ item.createdAt }}</span>
          </a-list-item>
        </template>
      </a-list>
    </a-col>

    <a-col :span="15">
      <a-empty v-if="!selectedTaskId" description="请从左侧选择一个任务查看完整过程追溯" />
      <div v-else>
        <a-space style="margin-bottom: 12px">
          <router-link :to="`/tasks/${selectedTaskId}`">在任务详情中查看（含步骤分配与处置操作）</router-link>
        </a-space>

        <!-- 对应5.7.1界面元素：计划版本列表，须保留全部历史版本（业务规则4） -->
        <a-card title="计划版本列表" size="small" v-if="planVersions.length">
          <a-collapse>
            <a-collapse-panel v-for="pv in planVersions" :key="pv.versionNo"
                               :header="`版本${pv.versionNo}（${sourceLabel(pv.source)}） - 冻结时间: ${pv.frozenAt || '未冻结'} - 可执行步骤数: ${pv.planSteps?.length ?? 0}`">
              <a-descriptions bordered :column="2" size="small">
                <a-descriptions-item label="结构校验">{{ checkLabel(pv.structureCheckResult) }}</a-descriptions-item>
                <a-descriptions-item label="能力校验">{{ checkLabel(pv.capabilityCheckResult) }}</a-descriptions-item>
                <a-descriptions-item label="约束校验">{{ checkLabel(pv.constraintCheckResult) }}</a-descriptions-item>
                <a-descriptions-item label="风险等级" v-if="pv.riskLevel">{{ pv.riskLevel }}</a-descriptions-item>
                <a-descriptions-item label="判定依据" :span="2" v-if="pv.judgmentBasis">{{ pv.judgmentBasis }}</a-descriptions-item>
              </a-descriptions>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <!-- 对应5.7.1界面元素：最终结果 -->
        <a-card title="最终结果" size="small" style="margin-top: 12px">
          <a-descriptions bordered :column="1" size="small">
            <a-descriptions-item label="任务终态">{{ statusLabel(selectedTask?.status) }}</a-descriptions-item>
            <a-descriptions-item label="完成/更新时间">{{ selectedTask?.updatedAt }}</a-descriptions-item>
            <a-descriptions-item label="结果摘要">{{ resultSummary }}</a-descriptions-item>
          </a-descriptions>
        </a-card>

        <!-- 对应5.7.1界面元素：事件类型筛选（多选，默认全选）、事件时间线 -->
        <a-card title="事件时间线" size="small" style="margin-top: 12px">
          <a-select v-model:value="eventTypeFilter" mode="multiple" allow-clear placeholder="按事件类型筛选（默认全部）"
                    style="width: 100%; margin-bottom: 12px" :options="eventTypeOptions" />
          <a-empty v-if="!filteredEvents.length" description="暂无事件记录" />
          <a-timeline v-else>
            <a-timeline-item v-for="e in filteredEvents" :key="e.id">
              {{ e.occurredAt }} - <b>{{ e.eventType }}</b> - {{ triggerLabel(e.trigger) }}
              <span v-if="e.reasonCode">（{{ e.reasonCode }}）</span>
              <div v-if="e.detailSummary">{{ e.detailSummary }}</div>
            </a-timeline-item>
          </a-timeline>
        </a-card>
      </div>
    </a-col>
  </a-row>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { listTasks, getTask, getTaskEvents, getPlanVersions } from '../../api/task'
import { listTaskDefinitions } from '../../api/taskDefinition'

const filters = reactive({ taskCode: '', taskFamily: undefined, status: undefined })
const taskDefinitions = ref([])
async function fetchTaskDefinitions() {
  const resp = await listTaskDefinitions()
  taskDefinitions.value = resp.data
}
// 对应5.7.1界面元素"时间范围"默认值：近7日
const timeRange = ref([dayjs().subtract(7, 'day').startOf('day'), dayjs().endOf('day')])
const taskList = ref([])
const selectedTaskId = ref(null)
const selectedTask = ref(null)
const planVersions = ref([])
const events = ref([])
const eventTypeFilter = ref([])

const statusOptions = [
  { key: 'PLANNING', label: '待规划' }, { key: 'SUPERVISING', label: '监督判定中' },
  { key: 'PENDING_ASSIGNMENT', label: '待分配' }, { key: 'DOWNGRADING', label: '降级执行中' },
  { key: 'EXECUTING', label: '执行中' }, { key: 'COMPLETED', label: '已完成' },
  { key: 'FAILED', label: '失败' }, { key: 'PENDING_MANUAL', label: '待人工处理' },
  { key: 'MANUAL_TERMINATED', label: '人工终止' }
]

function statusLabel(status) {
  return statusOptions.find((s) => s.key === status)?.label || status
}
function sourceLabel(source) {
  return source === 'BASELINE_TEMPLATE' ? '基线模板' : '自主规划'
}
function checkLabel(result) {
  if (!result) return '未执行'
  return result === 'PASS' ? '通过' : '不通过'
}
function triggerLabel(trigger) {
  return trigger === 'OPERATOR' ? '操作人' : '系统'
}

const IN_PROGRESS_STATUSES = ['PLANNING', 'SUPERVISING', 'PENDING_ASSIGNMENT', 'DOWNGRADING', 'EXECUTING']
const resultSummary = computed(() => {
  const t = selectedTask.value
  if (!t) return '—'
  const reason = t.failureReason || t.downgradeReason || t.manualTerminateReason
  if (reason) return reason
  if (t.status === 'COMPLETED') return '全部步骤完成条件均已满足，任务正常完成'
  if (t.status === 'PENDING_MANUAL') return '任务待人工处理，暂无自动结果摘要'
  if (IN_PROGRESS_STATUSES.includes(t.status)) return '任务正常推进中，尚未产生最终结果'
  return '—'
})

// 事件类型选项按当前任务实际出现过的类型动态生成，避免维护一份可能过时的全量枚举
const eventTypeOptions = computed(() =>
  [...new Set(events.value.map((e) => e.eventType))].map((t) => ({ value: t, label: t }))
)
const filteredEvents = computed(() => {
  if (!eventTypeFilter.value.length) return events.value
  return events.value.filter((e) => eventTypeFilter.value.includes(e.eventType))
})

async function fetchList() {
  const params = { taskCode: filters.taskCode || undefined, taskFamily: filters.taskFamily, status: filters.status, size: 50 }
  if (timeRange.value?.length === 2) {
    params.createdFrom = timeRange.value[0].format('YYYY-MM-DDTHH:mm:ss')
    params.createdTo = timeRange.value[1].format('YYYY-MM-DDTHH:mm:ss')
  }
  const resp = await listTasks(params)
  taskList.value = resp.data.content || resp.data
  // 异常路径3c：若此前选中的任务不在新的查询结果中，清空右侧详情，避免展示与筛选条件不符的追溯信息
  if (selectedTaskId.value && !taskList.value.some((t) => t.id === selectedTaskId.value)) {
    selectedTaskId.value = null
    selectedTask.value = null
  }
}

async function selectTask(item) {
  selectedTaskId.value = item.id
  eventTypeFilter.value = []
  const [taskResp, eventsResp, planResp] = await Promise.all([
    getTask(item.id), getTaskEvents(item.id), getPlanVersions(item.id)
  ])
  selectedTask.value = taskResp.data
  events.value = eventsResp.data
  planVersions.value = planResp.data
}

onMounted(() => {
  fetchList()
  fetchTaskDefinitions()
})
</script>

<style scoped>
.selected-item {
  background-color: #e6f4ff;
}
</style>
