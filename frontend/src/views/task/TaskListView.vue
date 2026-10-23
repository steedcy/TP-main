<template>
  <div>
    <a-space style="margin-bottom: 16px" wrap>
      <a-button type="primary" @click="submitVisible = true">提交任务</a-button>
      <a-input v-model:value="filterTaskCode" placeholder="任务编号" style="width: 180px" @pressEnter="fetchList" />
      <a-select v-model:value="filterStatus" style="width: 160px" placeholder="按状态筛选" allow-clear @change="fetchList">
        <a-select-option v-for="s in statusOptions" :key="s.key" :value="s.key">{{ s.label }}</a-select-option>
      </a-select>
      <a-select v-model:value="filterTaskFamily" style="width: 180px" placeholder="按任务族筛选" allow-clear @change="fetchList">
        <a-select-option v-for="d in allTaskDefinitions" :key="d.definitionCode" :value="d.definitionCode">{{ d.taskName }}</a-select-option>
      </a-select>
      <a-range-picker v-model:value="filterTimeRange" show-time format="YYYY-MM-DD HH:mm:ss" @change="fetchList" />
      <a-button @click="fetchList">查询</a-button>
    </a-space>

    <a-table :dataSource="list" :columns="columns" rowKey="id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag>{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a @click.stop="$router.push(`/tasks/${record.id}`)">详情</a>
            <a v-if="record.status === 'PLANNING' && record.missingInfoQuestions?.length"
               @click.stop="openClarify(record)">补充信息</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="submitVisible" title="提交任务目标" :confirmLoading="submitting"
             :okButtonProps="{ disabled: !form.taskGoal || form.taskGoal.length > 500 }" @ok="handleSubmit">
      <a-form :model="form" layout="vertical">
        <a-form-item label="任务目标（自然语言，1~500字，必填）">
          <a-textarea v-model:value="form.taskGoal" :rows="3" :maxlength="500" show-count />
        </a-form-item>
        <a-form-item label="任务族（可不选，系统自动判定）">
          <a-select v-model:value="form.taskFamily" allow-clear>
            <a-select-option v-for="d in enabledTaskDefinitions" :key="d.definitionCode" :value="d.definitionCode">{{ d.taskName }}</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 对应5.4.1：目标理解发现信息缺失时，逐条展示待补充问题；补充完成前不进入计划生成 -->
    <a-modal v-model:open="clarifyVisible" title="补充信息" :confirmLoading="clarifying"
             :okButtonProps="{ disabled: !allQuestionsAnswered }" @ok="handleClarifySubmit"
             @cancel="clarifyTaskId = null">
      <p>系统在目标理解中发现以下信息缺失，请逐条补充后重新提交：</p>
      <a-form layout="vertical">
        <a-form-item v-for="(q, idx) in clarifyQuestions" :key="idx" :label="q">
          <a-input v-model:value="clarifyAnswers[q]" />
        </a-form-item>
      </a-form>
      <a-button danger block @click="handleClarifyCancel">放弃并取消任务</a-button>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { listTasks, submitTask, clarifyTask, cancelTask } from '../../api/task'
import { listTaskDefinitions } from '../../api/taskDefinition'

const route = useRoute()
const list = ref([])
const submitVisible = ref(false)
const filterStatus = ref(route.query.status)
const filterTaskCode = ref('')
const filterTaskFamily = ref(undefined)
const filterTimeRange = ref([])
const form = reactive({ taskGoal: '', taskFamily: undefined })

// 任务族下拉数据源改为动态取任务定义（对应5.6.1），提交表单只展示已启用任务族，
// 筛选区仍需展示全部任务族（含已停用）以便查询历史任务
const allTaskDefinitions = ref([])
const enabledTaskDefinitions = computed(() => allTaskDefinitions.value.filter((d) => d.definitionStatus === 'ENABLED'))
async function fetchTaskDefinitions() {
  const resp = await listTaskDefinitions()
  allTaskDefinitions.value = resp.data
}

const statusOptions = [
  { key: 'PLANNING', label: '待规划' }, { key: 'SUPERVISING', label: '监督判定中' },
  { key: 'PENDING_ASSIGNMENT', label: '待分配' }, { key: 'DOWNGRADING', label: '降级执行中' },
  { key: 'EXECUTING', label: '执行中' }, { key: 'COMPLETED', label: '已完成' },
  { key: 'FAILED', label: '失败' }, { key: 'PENDING_MANUAL', label: '待人工处理' },
  { key: 'MANUAL_TERMINATED', label: '人工终止' }
]

const columns = [
  { title: '任务编号', dataIndex: 'taskCode' },
  { title: '任务目标', dataIndex: 'taskGoal' },
  { title: '任务族', dataIndex: 'taskFamily' },
  { title: '状态', key: 'status' },
  { title: '创建时间', dataIndex: 'createdAt' },
  { title: '操作', key: 'action' }
]

const submitting = ref(false)
const clarifyVisible = ref(false)
const clarifying = ref(false)
const clarifyTaskId = ref(null)
const clarifyQuestions = ref([])
const clarifyAnswers = reactive({})

const allQuestionsAnswered = computed(() =>
  clarifyQuestions.value.length > 0 && clarifyQuestions.value.every((q) => clarifyAnswers[q]?.trim())
)

function statusLabel(status) {
  return statusOptions.find((s) => s.key === status)?.label || status
}

async function fetchList() {
  const params = { status: filterStatus.value, taskCode: filterTaskCode.value || undefined, taskFamily: filterTaskFamily.value }
  if (filterTimeRange.value?.length === 2) {
    params.createdFrom = filterTimeRange.value[0].format('YYYY-MM-DDTHH:mm:ss')
    params.createdTo = filterTimeRange.value[1].format('YYYY-MM-DDTHH:mm:ss')
  }
  const resp = await listTasks(params)
  list.value = resp.data.content || resp.data
}

async function handleSubmit() {
  submitting.value = true
  try {
    const resp = await submitTask(form)
    message.success('任务已提交')
    closeSubmitModalAndRefresh()
    // 提交后立即触发目标理解；若信息不完整，直接引导补充，避免运行操作员再翻列表查找
    if (resp.data.status === 'PLANNING' && resp.data.missingInfoQuestions?.length) {
      openClarify(resp.data)
    }
  } catch (e) {
    // 4111（无在线设备代理）时任务未创建，保留弹窗以便修改后重试；
    // 其余业务异常（如4113目标理解超时、4112任务族无关）任务实例已按业务规则强制创建
    // （对应5.4.1后置条件），需关闭弹窗并刷新列表，否则运行操作员看不到已生成的任务
    if (e.response?.data?.code !== 4111) {
      closeSubmitModalAndRefresh()
    }
  } finally {
    submitting.value = false
  }
}

function closeSubmitModalAndRefresh() {
  submitVisible.value = false
  form.taskGoal = ''
  form.taskFamily = undefined
  fetchList()
}

function openClarify(task) {
  clarifyTaskId.value = task.id
  clarifyQuestions.value = task.missingInfoQuestions || []
  clarifyQuestions.value.forEach((q) => { clarifyAnswers[q] = clarifyAnswers[q] || '' })
  clarifyVisible.value = true
}

async function handleClarifySubmit() {
  clarifying.value = true
  try {
    const resp = await clarifyTask(clarifyTaskId.value, { ...clarifyAnswers })
    if (resp.data.missingInfoQuestions?.length) {
      // 补充后目标理解仍发现缺失，展示最新的待补充问题，直至信息完整（对应5.4.1业务规则）
      message.warning('信息仍不完整，请继续补充')
      openClarify(resp.data)
    } else {
      message.success('信息已补充，任务进入规划流程')
      clarifyVisible.value = false
      clarifyTaskId.value = null
    }
    fetchList()
  } finally {
    clarifying.value = false
  }
}

async function handleClarifyCancel() {
  await cancelTask(clarifyTaskId.value, '运行操作员在补充信息阶段放弃任务')
  message.success('任务已取消')
  clarifyVisible.value = false
  clarifyTaskId.value = null
  fetchList()
}

onMounted(() => {
  fetchList()
  fetchTaskDefinitions()
})
</script>
