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
      <a-form v-if="isOperator && task.status === 'PLANNING' && task.missingInfoQuestions?.length"
              layout="vertical" style="margin-top: 12px" @finish="handleClarify">
        <a-form-item v-for="question in task.missingInfoQuestions" :key="question" :label="question" required>
          <a-input v-model:value="clarificationAnswers[question]" :maxlength="500" />
        </a-form-item>
        <a-button type="primary" html-type="submit" :loading="clarifying">提交补充信息</a-button>
      </a-form>
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
      <a-tabs v-model:activeKey="activePlanTab">
        <a-tab-pane v-for="pv in planVersions" :key="pv.versionNo"
                    :tab="`版本${pv.versionNo}（${sourceLabel(pv.source)}）`">
          <a-descriptions bordered :column="2" size="small">
            <a-descriptions-item label="结构校验">{{ checkLabel(pv.structureCheckResult) }}</a-descriptions-item>
            <a-descriptions-item label="能力校验">{{ checkLabel(pv.capabilityCheckResult) }}</a-descriptions-item>
            <a-descriptions-item label="约束校验">{{ checkLabel(pv.constraintCheckResult) }}</a-descriptions-item>
            <a-descriptions-item label="冻结时间">{{ pv.frozenAt || '未冻结' }}</a-descriptions-item>
            <a-descriptions-item label="风险等级" v-if="pv.riskLevel">{{ pv.riskLevel }}</a-descriptions-item>
            <a-descriptions-item label="推荐处置" v-if="pv.riskLevel">{{ recommendedActionText(pv) }}</a-descriptions-item>
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

          <!-- 基线降级：原计划与所用模板的关联入口，以及目标/能力/五步限制的逐项匹配依据（DEF-S3-067） -->
          <template v-if="pv.source === 'BASELINE_TEMPLATE'">
            <a-descriptions bordered :column="2" size="small" style="margin-top: 8px" data-testid="baseline-template-ref">
              <a-descriptions-item label="计划来源">
                <a-tag color="blue">固定来源基线模板</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="原计划版本" v-if="priorPlanVersion(pv)">
                <a @click="activePlanTab = priorPlanVersion(pv).versionNo" data-testid="prior-plan-link">
                  版本{{ priorPlanVersion(pv).versionNo }}（{{ sourceLabel(priorPlanVersion(pv).source) }}）
                </a>
              </a-descriptions-item>
              <a-descriptions-item label="所用基线模板">
                <router-link v-if="pv.baselineTemplateId" to="/baseline-templates">
                  {{ templateRefOf(pv)?.name || ('模板#' + pv.baselineTemplateId) }}
                </router-link>
                <a-button
                  v-if="pv.baselineTemplateId"
                  type="link"
                  size="small"
                  style="margin-left: 8px"
                  @click="openBaselineTemplateModal(pv.baselineTemplateId)"
                  data-testid="view-baseline-template-btn"
                >
                  查看详情
                </a-button>
                <span v-else>—</span>
              </a-descriptions-item>
              <a-descriptions-item label="模板版本（冻结时）">
                <router-link v-if="pv.baselineTemplateId" to="/baseline-templates">
                  {{ templateRefOf(pv)?.version || '—' }}
                </router-link>
                <a-button
                  v-if="pv.baselineTemplateId"
                  type="link"
                  size="small"
                  style="margin-left: 8px"
                  @click="openBaselineTemplateModal(pv.baselineTemplateId)"
                  data-testid="view-frozen-template-btn"
                >
                  查看详情
                </a-button>
                <span v-else>{{ templateRefOf(pv)?.version || '—' }}</span>
                <span v-if="templateRefOf(pv)?.currentVersion && templateRefOf(pv).currentVersion !== templateRefOf(pv).version"
                      style="color: #999">（模板当前为 {{ templateRefOf(pv).currentVersion }}）</span>
              </a-descriptions-item>
              <a-descriptions-item label="降级原因" :span="2" v-if="task.downgradeReason">{{ task.downgradeReason }}</a-descriptions-item>
            </a-descriptions>
            <a-table :dataSource="matchRowsOf(pv)" size="small" :pagination="false" rowKey="item" style="margin-top: 8px"
                     :columns="[{ title: '匹配项', dataIndex: 'item' }, { title: '任务要求', dataIndex: 'expected' },
                                { title: '模板/计划', dataIndex: 'actual' }, { title: '结果', dataIndex: 'ok',
                                  customRender: ({ text }) => text ? '匹配' : '不匹配' }]" />
          </template>

          <!-- DEF-S3-036：候选计划摘要（步骤数、剩余额度、规划说明） -->
          <a-descriptions bordered :column="2" size="small" style="margin-top: 8px" data-testid="candidate-plan-summary">
            <a-descriptions-item label="可执行步骤数">{{ executableStepCount(pv) }} / 5</a-descriptions-item>
            <a-descriptions-item label="剩余步骤额度">{{ Math.max(0, 5 - executableStepCount(pv)) }}</a-descriptions-item>
            <a-descriptions-item label="规划说明" :span="2">{{ planNote(pv) }}</a-descriptions-item>
          </a-descriptions>
          <p style="margin-top: 8px"><b>候选步骤：</b></p>
          <a-table :dataSource="pv.planSteps" :columns="stepColumns" rowKey="stepSeq" size="small" :pagination="false">
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'inputParams'">
                <code>{{ JSON.stringify(record.inputParams ?? record.paramMapping ?? {}) }}</code>
              </template>
              <template v-else-if="column.key === 'paramSource'">{{ paramSourceOf(pv, record) }}</template>
              <template v-else-if="column.key === 'candidates'">{{ candidatesOf(pv, record) }}</template>
            </template>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <!-- 对应5.5.1步骤设备匹配与任务接受、5.5.2业务指令下发与执行反馈 -->
    <a-card title="步骤设备分配与执行情况" id="step-assignments" style="margin-top: 16px" v-if="stepAssignments.length">
      <div style="margin-bottom: 12px" data-testid="task-progress">
        <b>执行进度：</b>{{ progressLabel }}
        <a-progress :percent="progress.percent" size="small" style="max-width: 360px"
                    :status="progress.failed ? 'exception' : (progress.percent === 100 ? 'success' : 'active')" />
      </div>
      <a-table :dataSource="stepAssignments" :columns="stepAssignmentColumns" rowKey="id" size="small" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'stepSeq'">
            <span :id="`step-${record.stepSeq}`" :style="highlightStep === record.stepSeq ? 'background:#fffbe6;padding:0 4px' : ''">{{ record.stepSeq }}</span>
          </template>
          <template v-else-if="column.dataIndex === 'stepStatus'">
            <a-tag>{{ stepStatusLabel(record.stepStatus) }}</a-tag>
          </template>
          <template v-else-if="column.dataIndex === 'acceptanceResponseTime'">
            <span>{{ formatAcceptanceTime(record) }}</span>
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
          <span v-if="e.reasonCode" style="margin-left: 6px; color: #fa8c16">（原因码: {{ e.reasonCode }}）</span>
          <span v-if="e.detailSummary">：{{ e.detailSummary }}</span>
        </a-timeline-item>
      </a-timeline>
    </a-card>

    <a-card title="待人工处理" v-if="isOperator && task.status === 'PENDING_MANUAL'" style="margin-top: 16px">
      <a-space>
        <a-button @click="handleManualAction('SWITCH_TO_BASELINE')">转基线执行</a-button>
        <a-button id="btn-retry-planning" type="primary" @click="openRetryModal">重试规划</a-button>
        <a-button @click="handleManualAction('MARK_FAILED')" danger>置为失败</a-button>
        <a-button @click="terminateVisible = true" danger>终止任务</a-button>
      </a-space>
    </a-card>

    <!-- 对应5.5.6前置条件：PLANNING/SUPERVISING/PENDING_ASSIGNMENT/DOWNGRADING/EXECUTING均可终止，
         PENDING_MANUAL已在上方处置区提供终止入口，此处不重复展示 -->
    <a-card title="终止任务" v-else-if="isOperator && TERMINABLE_STATUSES.includes(task.status)" style="margin-top: 16px">
      <a-button danger @click="terminateVisible = true">终止任务</a-button>
    </a-card>

    <!-- 对应5.4.5异常路径4a与DEF-S3-091：待人工处理阶段允许操作员修改任务目标后重试规划 -->
    <a-modal v-model:open="retryModalVisible" title="重试规划" @ok="handleConfirmRetry" okText="确定" cancelText="取消" :okButtonProps="{ id: 'btn-confirm-retry', loading: retryLoading, disabled: !retryGoal || !retryGoal.trim() }">
      <a-alert type="info" show-icon style="margin-bottom: 12px"
               message="修改目标并重试规划"
               description="可在重试前修改任务目标，系统将基于新目标重新进行目标理解与候选计划生成；原计划版本将完整保留在历史列表中。" />
      <a-form layout="vertical">
        <a-form-item label="任务目标（1~500字，必填）" required>
          <a-textarea id="retry-task-goal" v-model:value="retryGoal" :maxlength="500" :auto-size="{ minRows: 3, maxRows: 6 }" show-count placeholder="请输入修改后的任务目标" />
        </a-form-item>
        <a-form-item label="处置原因（选填，不超过200字）">
          <a-input id="retry-reason" v-model:value="retryReason" :maxlength="200" placeholder="请输入处置原因" />
        </a-form-item>
      </a-form>
    </a-modal>

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

    <!-- 基线模板只读详情弹窗（DEF-S3-067） -->
    <a-modal
      v-model:open="templateModalVisible"
      title="基线模板详情（只读）"
      width="900px"
      :footer="null"
    >
      <div v-if="templateModalLoading" style="text-align: center; padding: 32px">
        <a-spin />
      </div>
      <template v-else-if="templateModalTarget">
        <a-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
          <a-descriptions-item label="模板名称">{{ templateModalTarget.templateName }}</a-descriptions-item>
          <a-descriptions-item label="模板意图">{{ templateModalTarget.templateIntent }}</a-descriptions-item>
          <a-descriptions-item label="模板版本">{{ formatVersion(templateModalTarget?.templateVersion) }}</a-descriptions-item>
          <a-descriptions-item label="模板状态">{{ templateModalTarget.templateStatus }}</a-descriptions-item>
          <a-descriptions-item label="步骤数量">{{ (templateModalTarget.steps || []).length }} / 5</a-descriptions-item>
          <a-descriptions-item label="模板属性">{{ templateModalTarget.isPreset ? '预置任务族模板' : '自定义模板' }}</a-descriptions-item>
        </a-descriptions>

        <a-divider orientation="left">模板输入参数</a-divider>
        <a-table
          :dataSource="templateModalTarget.inputParams || []"
          :columns="[
            { title: '参数名称', dataIndex: 'name' },
            { title: '类型', dataIndex: 'type' },
            { title: '必填', dataIndex: 'required', customRender: ({ text }) => text ? '是' : '否' },
            { title: '默认值', dataIndex: 'defaultValue', customRender: ({ text }) => text ?? '—' },
            { title: '取值范围/说明', dataIndex: 'range', customRender: ({ text }) => text || '—' }
          ]"
          :pagination="false"
          size="small"
          :rowKey="(r, idx) => r.name || idx"
          style="margin-bottom: 16px"
        />

        <a-divider orientation="left">步骤（顺序执行，最多5个）</a-divider>
        <div
          v-for="(step, idx) in (templateModalTarget.steps || [])"
          :key="step.stepSeq || idx"
          style="border: 1px solid #f0f0f0; border-radius: 4px; padding: 12px; margin-bottom: 12px; background: #fafafa"
        >
          <div style="font-weight: bold; margin-bottom: 8px">步骤 {{ step.stepSeq || (idx + 1) }}</div>
          <a-descriptions size="small" :column="2" bordered style="margin-bottom: 8px">
            <a-descriptions-item label="步骤所需能力">{{ capabilityLabel(step.capabilityType) || step.capabilityType }}</a-descriptions-item>
            <a-descriptions-item label="步骤超时时间（10~600秒）">{{ step.stepTimeout }} 秒</a-descriptions-item>
            <a-descriptions-item label="步骤完成条件" :span="2">{{ step.completionCondition }}</a-descriptions-item>
          </a-descriptions>

          <div style="font-weight: bold; margin: 8px 0 4px 0">参数映射：</div>
          <a-table
            :dataSource="step.paramMapping || []"
            :columns="[
              { title: '本步骤参数(target)', dataIndex: 'target' },
              { title: '来源(source)', dataIndex: 'source' }
            ]"
            :pagination="false"
            size="small"
            :rowKey="(r, i) => r.target || i"
          />
        </div>

        <div style="text-align: right; margin-top: 16px">
          <a-button @click="templateModalVisible = false">关闭</a-button>
        </div>
      </template>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../store/auth'
import { message } from 'ant-design-vue'
import { taskProgress, progressText } from '../../utils/taskProgress'
import { templateReference, matchBasis } from '../../utils/downgradeMatch'
import { getBaselineTemplate } from '../../api/baseline'
import { capabilityLabel } from '../../constants/capability'
import { getTask, getTaskEvents, getPlanVersions, getContextSnapshots, getStepAssignments, clarifyTask, manualAction, terminateTask } from '../../api/task'

const authStore = useAuthStore()
const isOperator = computed(() => authStore.role === 'OPERATOR')
const route = useRoute()
const taskId = route.params.taskId
const task = ref(null)
const events = ref([])
const planVersions = ref([])
const activePlanTab = ref(1)
function priorPlanVersion(pv) {
  if (!planVersions.value || planVersions.value.length <= 1) return null
  const prior = planVersions.value.filter((v) => v.versionNo < pv.versionNo)
  return prior.length ? prior[prior.length - 1] : null
}
const contextSnapshots = ref([])
const stepAssignments = ref([])
const currentSteps = computed(() => planVersions.value.find(p => p.id === task.value?.currentPlanVersionId)?.planSteps || [])
const progress = computed(() => taskProgress(currentSteps.value, stepAssignments.value))
const progressLabel = computed(() => progressText(progress.value))
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
    ? assignments.map(flightAssignmentSummary).join('；')
    : '未覆盖（计划缺少该渠道）' }
}))
// 从异常列表跳转时带?step=n，滚动并高亮对应步骤（DEF-S3-064）
const highlightStep = ref(route.query.step ? Number(route.query.step) : null)
const retryModalVisible = ref(false)
const retryGoal = ref('')
const retryReason = ref('')
const retryLoading = ref(false)
const terminateVisible = ref(false)
const terminateReason = ref('')
const confirmed = ref(false)
const clarificationAnswers = ref({})
const clarifying = ref(false)
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
  { title: '承接响应时间', dataIndex: 'acceptanceResponseTime' },
  { title: '下发时间', dataIndex: 'dispatchedAt' },
  { title: '反馈时间', dataIndex: 'feedbackAt' }
]

function formatAcceptanceTime(record) {
  if (record.acceptanceResponseTime) return record.acceptanceResponseTime
  if (record.acceptanceDurationMs != null) return record.acceptanceDurationMs + 'ms'
  const reqEvent = (events.value || []).find(e => e.eventType === 'AGENT_ASSIGNMENT_REQUESTED' && e.detailSummary && e.detailSummary.includes(`步骤${record.stepSeq}`))
  const accEvent = (events.value || []).find(e => (e.eventType === 'AGENT_ASSIGNED' || e.eventType === 'AGENT_REJECTED') && e.detailSummary && e.detailSummary.includes(`步骤${record.stepSeq}`))
  if (reqEvent && accEvent) {
    const diff = Math.max(0, new Date(accEvent.occurredAt).getTime() - new Date(reqEvent.occurredAt).getTime())
    return diff + 'ms'
  }
  return '-'
}

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
  { title: '输入参数', dataIndex: 'inputParams' },
  { title: '参数来源', key: 'paramSource' },
  { title: '候选设备', key: 'candidates' },
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
function recommendedActionText(pv) {
  const action = pv?.recommendedAction || (pv?.riskLevel === 'LOW' ? 'AUTO_EXECUTE' : pv?.riskLevel === 'HIGH' ? 'BASELINE_DOWNGRADE' : 'MANUAL_HANDLING')
  return action === 'AUTO_EXECUTE' ? '自动执行' : action === 'BASELINE_DOWNGRADE' ? '基线降级' : '转人工处理'
}
// DEF-S3-036：规划说明、参数来源与步骤候选设备，仅取页面已有的计划版本与上下文快照数据
function executableStepCount(pv) {
  if (!Array.isArray(pv?.planSteps)) return 0
  return pv.planSteps.filter((s) => !s.conditionNode && s.nodeType !== 'CONDITION' && s.stepType !== 'CONDITION').length
}
function planNote(pv) {
  const n = executableStepCount(pv)
  if (pv.source === 'BASELINE_TEMPLATE') return `基线模板${pv.snapshotId ? '（' + pv.snapshotId + '）' : ''}生成的 ${n} 步计划`
  const conf = pv.confidence != null ? `，置信度 ${pv.confidence}` : ''
  return `规划模型依据上下文快照${pv.snapshotId ? ' ' + pv.snapshotId : ''}生成 ${n} 步候选计划${conf}`
}
function paramSourceOf(pv, step) {
  if (pv.source === 'BASELINE_TEMPLATE') return '基线模板参数映射/任务场景参数'
  return Object.keys(step.inputParams || {}).length ? '规划模型依据任务目标与场景参数生成' : '无输入参数'
}
function candidatesOf(pv, step) {
  const snap = contextSnapshots.value.find((s) => s.snapshotCode === pv.snapshotId)
  let agents = snap?.agents
  if (typeof agents === 'string') {
    try { agents = JSON.parse(agents) } catch (e) { agents = [] }
  }
  if (!Array.isArray(agents)) agents = []
  const names = agents
    .filter((a) => a.onlineStatus === 'ONLINE' && (a.capabilities || []).includes(step.capabilityType))
    .map((a) => a.agentId)
  return names.length ? names.join('，') : '无在线候选设备（或快照不可用）'
}
function checkLabel(result) {
  if (!result) return '未执行'
  return result === 'PASS' ? '通过' : '不通过'
}
function stepStatusLabel(status) {
  const map = { PENDING_ASSIGNMENT: '待分配', EXECUTING: '执行中', COMPLETED: '已完成', FAILED: '失败', FROZEN: '已冻结', SKIPPED: '条件分支跳过' }
  return map[status] || status
}
function flightAssignmentSummary(assignment) {
  if (assignment.stepStatus === 'SKIPPED' && assignment.reasonCode === 'FLIGHT_CHANNEL_UNAVAILABLE') {
    return '未覆盖（无在线空闲的正确渠道设备）'
  }
  const started = Date.parse(assignment.dispatchedAt)
  const ended = Date.parse(assignment.feedbackAt)
  const responseTime = Number.isFinite(started) && Number.isFinite(ended)
    ? `，响应时长 ${Math.max(0, ((ended - started) / 1000)).toFixed(1)} 秒` : ''
  return `${assignment.deviceAgentCode || '未分配'}：${stepStatusLabel(assignment.stepStatus)}`
    + `${assignment.feedbackAt ? `，完成时间 ${assignment.feedbackAt}${responseTime}` : ''}`
}

async function fetchAll() {
  const [taskResp, eventsResp, planResp, snapResp, stepResp] = await Promise.all([
    getTask(taskId), getTaskEvents(taskId), getPlanVersions(taskId), getContextSnapshots(taskId), getStepAssignments(taskId)
  ])
  task.value = taskResp.data
  events.value = eventsResp.data
  planVersions.value = planResp.data
  if (planResp.data?.length) {
    activePlanTab.value = planResp.data[planResp.data.length - 1].versionNo
  }
  contextSnapshots.value = snapResp.data
  stepAssignments.value = stepResp.data
  await loadTemplates(planResp.data)
  scrollToHighlightedStep()
}

// 基线计划版本用到的模板详情（只取一次）；取不到时页面仍显示模板编号，匹配依据标为不匹配而不是默认通过
const templates = ref({})
async function loadTemplates(versions) {
  const ids = [...new Set((versions || []).filter(v => v.source === 'BASELINE_TEMPLATE' && v.baselineTemplateId)
    .map(v => v.baselineTemplateId))].filter(id => !(id in templates.value))
  await Promise.all(ids.map(async (id) => {
    try { templates.value = { ...templates.value, [id]: (await getBaselineTemplate(id)).data } }
    catch (e) { templates.value = { ...templates.value, [id]: null } }
  }))
}
const templateRefOf = (pv) => templateReference(pv, templates.value[pv.baselineTemplateId])
const matchRowsOf = (pv) => matchBasis(task.value, pv, templates.value[pv.baselineTemplateId])

let scrolled = false
function scrollToHighlightedStep() {
  if (scrolled || highlightStep.value == null) return
  nextTick(() => {
    const el = document.getElementById(`step-${highlightStep.value}`)
    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); scrolled = true }
  })
}

function openRetryModal() {
  retryGoal.value = task.value?.taskGoal || ''
  retryReason.value = ''
  retryModalVisible.value = true
}

async function handleConfirmRetry() {
  if (!retryGoal.value || !retryGoal.value.trim()) {
    message.warning('任务目标不能为空')
    return
  }
  retryLoading.value = true
  try {
    const cleanGoal = retryGoal.value.trim()
    const cleanReason = retryReason.value?.trim() || null
    const response = await manualAction(taskId, 'RETRY_PLANNING', cleanReason, cleanGoal)
    retryModalVisible.value = false
    await fetchAll()
    if (response.data.status === 'PENDING_MANUAL') {
      message.warning(response.data.failureReason || '重试规划未通过校验，任务仍待人工处理')
    } else {
      message.success('重试规划已提交')
    }
  } catch (err) {
    // 错误在全局提示
  } finally {
    retryLoading.value = false
  }
}

async function handleManualAction(action) {
  if (action === 'RETRY_PLANNING') {
    openRetryModal()
    return
  }
  const response = await manualAction(taskId, action)
  await fetchAll()
  if (response.data.status === 'PENDING_MANUAL') {
    message.warning(response.data.failureReason || '处置未通过校验，任务仍待人工处理')
  } else {
    message.success('操作已提交')
  }
}

async function handleClarify() {
  const questions = task.value?.missingInfoQuestions || []
  if (questions.some(question => !clarificationAnswers.value[question]?.trim())) {
    message.warning('请逐条回答待补充问题')
    return
  }
  clarifying.value = true
  try {
    await clarifyTask(taskId, Object.fromEntries(questions.map(question => [question, clarificationAnswers.value[question].trim()])))
    clarificationAnswers.value = {}
    await fetchAll()
    message.success(task.value?.missingInfoQuestions?.length ? '补充已保存，请继续回答新问题' : '补充已保存')
  } finally {
    clarifying.value = false
  }
}

const templateModalVisible = ref(false)
const templateModalTarget = ref(null)
const templateModalLoading = ref(false)

async function openBaselineTemplateModal(templateId) {
  if (!templateId) return
  if (templates.value[templateId]) {
    templateModalTarget.value = templates.value[templateId]
    templateModalVisible.value = true
    return
  }
  templateModalLoading.value = true
  templateModalVisible.value = true
  try {
    const resp = await getBaselineTemplate(templateId)
    templateModalTarget.value = resp.data
  } catch (err) {
    message.error('获取基线模板详情失败')
  } finally {
    templateModalLoading.value = false
  }
}

function formatVersion(v) {
  if (!v) return '—'
  return String(v).startsWith('V') ? String(v) : 'V' + v
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
    if (task.value && TERMINABLE_STATUSES.includes(task.value.status)) {
      fetchAll()
    }
  }, 10000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
