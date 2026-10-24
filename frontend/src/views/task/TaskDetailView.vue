<template>
  <div v-if="task">
    <a-descriptions bordered :column="2">
      <a-descriptions-item label="任务编号">{{ task.taskCode }}</a-descriptions-item>
      <a-descriptions-item label="状态"><a-tag>{{ statusLabel(task.status) }}</a-tag></a-descriptions-item>
      <a-descriptions-item label="任务目标" :span="2">{{ task.taskGoal }}</a-descriptions-item>
      <a-descriptions-item label="任务族">{{ task.taskFamily || '未指定' }}</a-descriptions-item>
      <a-descriptions-item label="失败/降级原因" v-if="task.failureReason || task.downgradeReason">
        {{ task.failureReason || task.downgradeReason }}
      </a-descriptions-item>
    </a-descriptions>

    <!-- 对应5.4.1界面元素：解析结果、待补充问题 -->
    <a-card title="目标理解结果" style="margin-top: 16px" v-if="task.goalParsingResult || task.missingInfoQuestions?.length">
      <a-descriptions bordered :column="1" v-if="task.goalParsingResult">
        <a-descriptions-item label="起点">{{ task.goalParsingResult.origin || '—' }}</a-descriptions-item>
        <a-descriptions-item label="目的地">{{ task.goalParsingResult.destination || '—' }}</a-descriptions-item>
        <a-descriptions-item label="约束条件">{{ (task.goalParsingResult.constraints || []).join('；') || '—' }}</a-descriptions-item>
        <a-descriptions-item label="完成条件">{{ task.goalParsingResult.completionCondition || '—' }}</a-descriptions-item>
      </a-descriptions>
      <a-alert v-if="task.missingInfoQuestions?.length" type="warning" show-icon style="margin-top: 8px"
               message="待补充问题" :description="task.missingInfoQuestions.join('；')" />
    </a-card>

    <!-- 对应5.4.2规划上下文构建：参与规划的代理清单、能力覆盖情况、快照生成时间 -->
    <a-card title="规划依据（上下文快照）" style="margin-top: 16px" v-if="contextSnapshots.length">
      <a-collapse>
        <a-collapse-panel v-for="snap in contextSnapshots" :key="snap.id"
                           :header="`${snap.snapshotCode} - 生成时间: ${snap.generatedAt}`">
          <p><b>能力覆盖：</b>{{ JSON.stringify(snap.capabilityCoverage) }}</p>
          <p><b>参与规划的代理：</b></p>
          <pre>{{ JSON.stringify(snap.agents, null, 2) }}</pre>
          <p v-if="snap.failedAgentCodes?.length"><b>查询失败的代理：</b>{{ snap.failedAgentCodes.join('，') }}</p>
        </a-collapse-panel>
      </a-collapse>
    </a-card>

    <!-- 对应5.4.3~5.4.6：候选步骤、三类校验结果与错误清单、监督判定、降级信息 -->
    <a-card title="计划版本与校验/判定结果" style="margin-top: 16px" v-if="planVersions.length">
      <a-tabs>
        <a-tab-pane v-for="pv in planVersions" :key="pv.versionNo"
                    :tab="`版本${pv.versionNo}（${sourceLabel(pv.source)}）`">
          <a-descriptions bordered :column="2" size="small">
            <a-descriptions-item label="结构校验">{{ checkLabel(pv.structureCheckResult) }}</a-descriptions-item>
            <a-descriptions-item label="能力校验">{{ checkLabel(pv.capabilityCheckResult) }}</a-descriptions-item>
            <a-descriptions-item label="约束校验">{{ checkLabel(pv.constraintCheckResult) }}</a-descriptions-item>
            <a-descriptions-item label="冻结时间">{{ pv.frozenAt || '未冻结' }}</a-descriptions-item>
            <a-descriptions-item label="风险等级" v-if="pv.riskLevel">{{ pv.riskLevel }}</a-descriptions-item>
            <a-descriptions-item label="风险原因" v-if="pv.riskReasonCode">{{ pv.riskReasonCode }}</a-descriptions-item>
            <a-descriptions-item label="判定依据" :span="2" v-if="pv.judgmentBasis">{{ pv.judgmentBasis }}</a-descriptions-item>
            <a-descriptions-item label="置信度" v-if="pv.confidence != null">{{ pv.confidence }}</a-descriptions-item>
            <a-descriptions-item label="规则集版本" v-if="pv.ruleSetVersion">{{ pv.ruleSetVersion }}</a-descriptions-item>
          </a-descriptions>

          <a-alert v-if="pv.validationErrors?.length" type="error" show-icon style="margin: 8px 0"
                    message="校验错误清单">
            <template #description>
              <ul>
                <li v-for="(err, i) in pv.validationErrors" :key="i">
                  [{{ err.errorType }}] 步骤{{ err.stepSeq ?? '—' }}：{{ err.description }}（{{ err.reasonCode }}）
                </li>
              </ul>
            </template>
          </a-alert>

          <p style="margin-top: 8px"><b>候选步骤：</b></p>
          <a-table :dataSource="pv.planSteps" :columns="stepColumns" rowKey="stepSeq" size="small" :pagination="false" />
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <!-- 对应5.5.1步骤设备匹配与任务接受、5.5.2业务指令下发与执行反馈 -->
    <a-card title="步骤设备分配与执行情况" style="margin-top: 16px" v-if="stepAssignments.length">
      <a-table :dataSource="stepAssignments" :columns="stepAssignmentColumns" rowKey="id" size="small" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'stepStatus'">
            <a-tag>{{ stepStatusLabel(record.stepStatus) }}</a-tag>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-card v-if="task.taskFamily === 'FLIGHT_CHANGE_RESPONSE'" title="航班变更渠道响应" style="margin-top: 16px">
      <a-descriptions bordered :column="1">
        <a-descriptions-item v-for="channel in flightChannelResults" :key="channel.name" :label="channel.name">
          {{ channel.summary }}
        </a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-card v-if="task.taskFamily === 'OVERSIZE_BAGGAGE_HANDLING' && baggageResult" title="行李测量与超规判定" style="margin-top: 16px">
      <a-descriptions bordered :column="2">
        <a-descriptions-item label="长×宽×高">{{ baggageResult.length }}×{{ baggageResult.width }}×{{ baggageResult.height }} cm</a-descriptions-item>
        <a-descriptions-item label="重量">{{ baggageResult.weight }} kg</a-descriptions-item>
        <a-descriptions-item label="超规判定">{{ baggageResult.isOversize ? '超规' : '非超规' }}</a-descriptions-item>
        <a-descriptions-item label="阈值">三边和 ＞ {{ baggageResult.dimensionThresholdCm }} cm 或重量 ＞ {{ baggageResult.weightThresholdKg }} kg</a-descriptions-item>
        <a-descriptions-item label="阈值来源" :span="2">{{ baggageResult.thresholdSource || '未记录' }}</a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-card title="事件时间线（只读，事件仅可追加不可修改删除，对应5.7.1）" style="margin-top: 16px">
      <a-timeline>
        <a-timeline-item v-for="e in events" :key="e.id">
          {{ e.occurredAt }} - {{ e.eventType }}
          <span v-if="e.detailSummary">：{{ e.detailSummary }}</span>
        </a-timeline-item>
      </a-timeline>
    </a-card>

    <a-card title="待人工处理" v-if="isOperator && task.status === 'PENDING_MANUAL'" style="margin-top: 16px">
      <a-space>
        <a-button @click="handleManualAction('SWITCH_TO_BASELINE')">转基线执行</a-button>
        <a-button @click="handleManualAction('RETRY_PLANNING')">重试规划</a-button>
        <a-button @click="handleManualAction('MARK_FAILED')" danger>置为失败</a-button>
        <a-button @click="terminateVisible = true" danger>终止任务</a-button>
      </a-space>
    </a-card>

    <!-- 对应5.5.6前置条件：PLANNING/SUPERVISING/PENDING_ASSIGNMENT/DOWNGRADING/EXECUTING均可终止，
         PENDING_MANUAL已在上方处置区提供终止入口，此处不重复展示 -->
    <a-card title="终止任务" v-else-if="isOperator && TERMINABLE_STATUSES.includes(task.status)" style="margin-top: 16px">
      <a-button danger @click="terminateVisible = true">终止任务</a-button>
    </a-card>

    <!-- 对应5.5.6业务规则1/5：原因1~200字+二次确认缺一不可；责任边界固定文案，人工终止不等同于设备安全急停 -->
    <a-modal v-model:open="terminateVisible" title="人工终止任务" @ok="handleTerminate" :okButtonProps="{ disabled: !confirmed || !terminateReason }">
      <a-alert type="warning" show-icon style="margin-bottom: 12px"
               message="责任边界提示"
               description="人工终止仅停止后续业务步骤下发并释放设备占用，不等同于设备安全急停；已完成步骤结果保留，不回滚不补偿。请核实设备现场实际状态。" />
      <a-form layout="vertical">
        <a-form-item label="终止原因（1~200字，必填）">
          <a-textarea v-model:value="terminateReason" :maxlength="200" show-count />
        </a-form-item>
        <a-form-item>
          <a-checkbox v-model:checked="confirmed">
            我已阅读并确认上述责任边界提示，确认终止此任务
          </a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../store/auth'
import { message } from 'ant-design-vue'
import { getTask, getTaskEvents, getPlanVersions, getContextSnapshots, getStepAssignments, manualAction, terminateTask } from '../../api/task'

const authStore = useAuthStore()
const isOperator = computed(() => authStore.role === 'OPERATOR')
const route = useRoute()
const taskId = route.params.taskId
const task = ref(null)
const events = ref([])
const planVersions = ref([])
const contextSnapshots = ref([])
const stepAssignments = ref([])
const currentSteps = computed(() => planVersions.value.find(p => p.id === task.value?.currentPlanVersionId)?.planSteps || [])
const baggageResult = computed(() => stepAssignments.value
  .find(a => currentSteps.value.find(s => s.stepSeq === a.stepSeq)?.capabilityType === 'CAP_BAGGAGE_MEASURE')?.outputParams || null)
const flightChannelResults = computed(() => [
  { name: '航延屏', capabilities: ['CAP_FLIGHT_UPDATE'] },
  { name: '智慧航显', capabilities: ['CAP_INFO_DISPLAY'] },
  { name: '机器人', capabilities: ['CAP_NOTIFICATION', 'CAP_NAVIGATION'] }
].map(channel => {
  const assignments = stepAssignments.value.filter(a => channel.capabilities.includes(
    currentSteps.value.find(s => s.stepSeq === a.stepSeq)?.capabilityType))
  return { name: channel.name, summary: assignments.length
    ? assignments.map(a => `${a.deviceAgentCode || '未分配'}：${stepStatusLabel(a.stepStatus)}${a.feedbackAt ? `，反馈时间 ${a.feedbackAt}` : ''}`).join('；')
    : '未覆盖（计划缺少该渠道）' }
}))
const terminateVisible = ref(false)
const terminateReason = ref('')
const confirmed = ref(false)
let pollTimer = null

/** 可终止状态：PLANNING/SUPERVISING/PENDING_ASSIGNMENT/DOWNGRADING/EXECUTING/PENDING_MANUAL（对应5.5.6前置条件） */
const TERMINABLE_STATUSES = ['PLANNING', 'SUPERVISING', 'PENDING_ASSIGNMENT', 'DOWNGRADING', 'EXECUTING', 'PENDING_MANUAL']

const stepAssignmentColumns = [
  { title: '步骤', dataIndex: 'stepSeq' },
  { title: '分配设备', dataIndex: 'deviceAgentCode' },
  { title: '指令编号', dataIndex: 'commandId' },
  { title: '步骤状态', dataIndex: 'stepStatus' },
  { title: '重试次数', dataIndex: 'retryCount' },
  { title: '执行结果', dataIndex: 'executionResult' },
  { title: '下发时间', dataIndex: 'dispatchedAt' },
  { title: '反馈时间', dataIndex: 'feedbackAt' }
]

const statusOptions = [
  { key: 'PLANNING', label: '待规划' }, { key: 'SUPERVISING', label: '监督判定中' },
  { key: 'PENDING_ASSIGNMENT', label: '待分配' }, { key: 'DOWNGRADING', label: '降级执行中' },
  { key: 'EXECUTING', label: '执行中' }, { key: 'COMPLETED', label: '已完成' },
  { key: 'FAILED', label: '失败' }, { key: 'PENDING_MANUAL', label: '待人工处理' },
  { key: 'MANUAL_TERMINATED', label: '人工终止' }
]
const stepColumns = [
  { title: '步骤', dataIndex: 'stepSeq' },
  { title: '步骤目标', dataIndex: 'stepGoal' },
  { title: '所需能力', dataIndex: 'capabilityType' },
  { title: '前置条件', dataIndex: 'precondition' },
  { title: '完成条件', dataIndex: 'completionCondition' },
  { title: '失败处理', dataIndex: 'failureHandling' }
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
function stepStatusLabel(status) {
  const map = { PENDING_ASSIGNMENT: '待分配', EXECUTING: '执行中', COMPLETED: '已完成', FAILED: '失败', FROZEN: '已冻结', SKIPPED: '条件分支跳过' }
  return map[status] || status
}

async function fetchAll() {
  const [taskResp, eventsResp, planResp, snapResp, stepResp] = await Promise.all([
    getTask(taskId), getTaskEvents(taskId), getPlanVersions(taskId), getContextSnapshots(taskId), getStepAssignments(taskId)
  ])
  task.value = taskResp.data
  events.value = eventsResp.data
  planVersions.value = planResp.data
  contextSnapshots.value = snapResp.data
  stepAssignments.value = stepResp.data
}

async function handleManualAction(action) {
  await manualAction(taskId, action)
  message.success('操作已提交')
  fetchAll()
}

async function handleTerminate() {
  if (!confirmed.value || !terminateReason.value) {
    message.warning('请填写终止原因并勾选二次确认')
    return
  }
  await terminateTask(taskId, terminateReason.value)
  message.success('任务已终止')
  terminateVisible.value = false
  fetchAll()
}

/** 对应5.5.5业务规则9：执行中任务详情刷新周期不超过15秒 */
onMounted(() => {
  fetchAll()
  pollTimer = setInterval(() => {
    if (task.value && ['EXECUTING', 'DOWNGRADING', 'SUPERVISING'].includes(task.value.status)) {
      fetchAll()
    }
  }, 10000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
