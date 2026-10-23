<template>
  <div>
    <a-alert message="步骤数硬限5个，第6步禁止添加；预置任务族模板不可删除，仅可停用" type="warning" style="margin-bottom: 16px" />
    <a-button type="primary" style="margin-bottom: 16px" @click="openForm(null)">新增模板</a-button>

    <a-table :dataSource="templates" :columns="columns" rowKey="id" :loading="listLoading">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'templateIntent'">
          {{ taskDefinitionLabel(record.templateIntent) }}
        </template>
        <template v-else-if="column.key === 'templateStatus'">
          <a-tag :color="statusColor(record.templateStatus)">{{ statusLabel(record.templateStatus) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space wrap>
            <a-button size="small" @click="openForm(record)">编辑</a-button>
            <a-button size="small" @click="openDryRun(record)">试运行</a-button>
            <a-button
              size="small" type="primary"
              :disabled="record.templateStatus !== 'DRY_RUN_PASSED'"
              @click="handleEnable(record)"
            >
              启用
            </a-button>
            <a-popconfirm v-if="record.templateStatus === 'ENABLED'" title="停用后模板退出降级可选集合，确认停用？" @confirm="handleDisable(record)">
              <a-button size="small" danger>停用</a-button>
            </a-popconfirm>
            <a-tooltip v-if="record.isPreset" title="预置任务族模板不可删除">
              <a-button size="small" danger disabled>删除</a-button>
            </a-tooltip>
            <a-popconfirm v-else title="确认删除该模板？" @confirm="handleDelete(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="formVisible"
      :title="isEdit ? '编辑模板' : '新增模板'"
      width="900px"
      @ok="handleSubmit"
      :confirmLoading="submitLoading"
    >
      <a-form ref="formRef" :model="form" :rules="formRules" layout="vertical">
        <a-form-item label="模板名称" name="templateName">
          <a-input v-model:value="form.templateName" :disabled="isEdit" maxlength="64" />
        </a-form-item>
        <a-form-item label="模板意图" name="templateIntent">
          <a-select v-model:value="form.templateIntent" :disabled="isEdit">
            <a-select-option v-for="d in taskDefinitions" :key="d.definitionCode" :value="d.definitionCode">{{ d.taskName }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模板输入参数">
          <ParamTableEditor v-model="form.inputParams" mode="input" />
        </a-form-item>

        <a-divider>步骤（顺序执行，最多5个）</a-divider>
        <div v-for="(step, idx) in form.steps" :key="step.__key" style="border: 1px solid #f0f0f0; padding: 12px; margin-bottom: 12px">
          <a-row justify="space-between" style="margin-bottom: 8px">
            <a-col><b>步骤 {{ idx + 1 }}</b></a-col>
            <a-col>
              <a-space>
                <a-button size="small" :disabled="idx === 0" @click="moveStep(idx, -1)">上移</a-button>
                <a-button size="small" :disabled="idx === form.steps.length - 1" @click="moveStep(idx, 1)">下移</a-button>
                <a-button size="small" danger @click="removeStep(idx)">删除</a-button>
              </a-space>
            </a-col>
          </a-row>
          <a-form-item label="步骤所需能力">
            <a-select v-model:value="step.capabilityType" placeholder="取值来自已启用能力类型" style="width: 300px">
              <a-select-option v-for="c in CAPABILITY_TYPES" :key="c.value" :value="c.value">{{ c.label }}</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="参数映射">
            <ParamMappingEditor v-model="step.paramMapping" />
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="8">
              <a-form-item label="步骤超时时间（10~600秒）">
                <a-input-number v-model:value="step.stepTimeout" :min="10" :max="600" style="width: 100%" />
              </a-form-item>
            </a-col>
            <a-col :span="16">
              <a-form-item label="步骤完成条件">
                <a-input v-model:value="step.completionCondition" placeholder="描述判定该步骤完成的输出条件" />
              </a-form-item>
            </a-col>
          </a-row>
        </div>
        <a-button type="dashed" block :disabled="form.steps.length >= 5" @click="addStep">
          + 添加步骤（{{ form.steps.length }}/5）
        </a-button>
      </a-form>
    </a-modal>

    <a-modal v-model:open="dryRunVisible" title="试运行" width="900px" :footer="null">
      <template v-if="dryRunTarget">
        <a-descriptions :column="2" size="small" style="margin-bottom: 16px">
          <a-descriptions-item label="目标模板">{{ dryRunTarget.templateName }}</a-descriptions-item>
          <a-descriptions-item label="模板版本">{{ dryRunTarget.templateVersion }}</a-descriptions-item>
          <a-descriptions-item label="计划来源标识">基线模板</a-descriptions-item>
        </a-descriptions>

        <template v-if="!dryRunResult">
          <a-form layout="vertical">
            <a-form-item v-for="p in dryRunTarget.inputParams" :key="p.name" :label="`${p.name}（${p.type}）`">
              <a-input v-model:value="dryRunForm.inputParams[p.name]" :placeholder="p.defaultValue || ''" />
            </a-form-item>
            <a-divider>为每个步骤选择模拟设备</a-divider>
            <a-form-item v-for="s in dryRunTarget.steps" :key="s.stepSeq" :label="`步骤${s.stepSeq}（${capabilityLabel(s.capabilityType)}）`">
              <a-select v-model:value="dryRunForm.deviceByStep[s.stepSeq]" placeholder="选择具备该能力的仿真体或设备" style="width: 100%">
                <a-select-option v-for="agent in agentOptions" :key="agent.agentId" :value="agent.agentId">
                  {{ agent.agentId }} - {{ agent.deviceName }}
                </a-select-option>
              </a-select>
            </a-form-item>
            <a-button type="primary" :loading="dryRunLoading" @click="handleStartDryRun">开始试运行</a-button>
          </a-form>
        </template>

        <template v-else>
          <a-alert
            :message="`总体结果: ${({SUCCESS:'成功',RUNNING:'执行中',FAILED:'失败',CANCELLED:'已取消'})[dryRunResult.result]}`"
            :type="dryRunResult.result === 'SUCCESS' ? 'success' : dryRunResult.result === 'RUNNING' ? 'info' : 'error'"
            style="margin-bottom: 16px"
          />
          <a-table
            :dataSource="dryRunResult.stepResults" :pagination="false" size="small" rowKey="stepSeq"
            style="margin-bottom: 16px"
            :columns="[
              { title: '步骤', dataIndex: 'stepSeq' },
              { title: '结果', dataIndex: 'result' },
              { title: '耗时(秒)', dataIndex: 'duration' },
              { title: '失败原因', dataIndex: 'failureReason' }
            ]"
          />
          <a-divider>事件时间线</a-divider>
          <a-timeline>
            <a-timeline-item v-for="(e, i) in dryRunResult.events" :key="i">
              <b>{{ e.eventType }}</b>（{{ e.trigger }}）{{ e.detailSummary }} - {{ e.occurredAt }}
            </a-timeline-item>
          </a-timeline>
          <a-button v-if="dryRunResult.result === 'RUNNING'" danger style="margin-top: 12px" @click="handleCancelDryRun">取消试运行</a-button>
          <a-button v-else style="margin-top: 12px" @click="dryRunResult = null">重新试运行</a-button>
        </template>
      </template>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  listBaselineTemplates, getBaselineTemplate, createBaselineTemplate, updateBaselineTemplate,
  getBaselineDryRun, cancelBaselineDryRun, dryRunBaselineTemplate, enableBaselineTemplate, disableBaselineTemplate, deleteBaselineTemplate
} from '../../api/baseline'
import { listAgents } from '../../api/device'
import { listTaskDefinitions } from '../../api/taskDefinition'
import { CAPABILITY_TYPES, capabilityLabel } from '../../constants/capability'
import ParamTableEditor from '../../components/ParamTableEditor.vue'
import ParamMappingEditor from '../../components/ParamMappingEditor.vue'

const templates = ref([])
// 模板意图下拉改为动态取任务定义（对应5.6.1联动），取代硬编码4值枚举，扩展任务族也可配置降级模板
const taskDefinitions = ref([])
function taskDefinitionLabel(code) {
  return taskDefinitions.value.find((d) => d.definitionCode === code)?.taskName || code
}
async function fetchTaskDefinitions() {
  const resp = await listTaskDefinitions()
  taskDefinitions.value = resp.data
}
const listLoading = ref(false)
const columns = [
  { title: '模板名称', dataIndex: 'templateName' },
  { title: '模板意图', key: 'templateIntent' },
  { title: '步骤数', customRender: ({ record }) => `${(record.steps || []).length} / 5` },
  { title: '版本', dataIndex: 'templateVersion' },
  { title: '状态', key: 'templateStatus' },
  { title: '操作', key: 'action', width: 380 }
]

function statusLabel(s) {
  return { DRAFT: '草稿', DRY_RUN_PASSED: '试运行通过', ENABLED: '已启用', DISABLED: '已停用' }[s] || s
}
function statusColor(s) {
  return { DRAFT: 'default', DRY_RUN_PASSED: 'blue', ENABLED: 'green', DISABLED: 'default' }[s]
}

async function fetchList() {
  listLoading.value = true
  try {
    const resp = await listBaselineTemplates()
    templates.value = resp.data
  } finally {
    listLoading.value = false
  }
}

const formVisible = ref(false)
const submitLoading = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const editingId = ref(null)
let paramKeySeq = 0
let stepKeySeq = 0
const withParamKeys = (params) => (params || []).map(p => ({ ...p, __key: `p${paramKeySeq++}` }))
const withMappingKeys = (mappings) => (mappings || []).map(m => ({ ...m, __key: `mm${paramKeySeq++}` }))
const emptyForm = () => ({ templateName: '', templateIntent: undefined, inputParams: [], steps: [] })
const form = reactive(emptyForm())
const formRules = {
  templateName: [{ required: true, message: '请输入模板名称' }, { max: 64, message: '最长64位' }],
  templateIntent: [{ required: true, message: '请选择模板意图' }]
}

function newStep() {
  return { __key: `s${stepKeySeq++}`, capabilityType: undefined, paramMapping: [], stepTimeout: 60, completionCondition: '' }
}
function addStep() {
  if (form.steps.length >= 5) return
  form.steps.push(newStep())
}
function removeStep(idx) {
  form.steps.splice(idx, 1)
}
function moveStep(idx, dir) {
  const target = idx + dir
  if (target < 0 || target >= form.steps.length) return
  const [item] = form.steps.splice(idx, 1)
  form.steps.splice(target, 0, item)
}

async function openForm(record) {
  isEdit.value = !!record
  editingId.value = record?.id || null
  if (record) {
    const detail = (await getBaselineTemplate(record.id)).data
    Object.assign(form, {
      templateName: detail.templateName, templateIntent: detail.templateIntent,
      inputParams: withParamKeys(detail.inputParams),
      steps: (detail.steps || []).map(s => ({ ...s, __key: `s${stepKeySeq++}`, paramMapping: withMappingKeys(s.paramMapping) }))
    })
  } else {
    Object.assign(form, emptyForm())
  }
  formVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  if (!form.inputParams.length) {
    message.warning('请定义至少1个输入参数')
    return
  }
  if (!form.steps.length) {
    message.warning('请添加至少1个步骤')
    return
  }
  for (const s of form.steps) {
    if (!s.capabilityType) {
      message.warning('请为每个步骤选择所需能力')
      return
    }
    if (!s.paramMapping.length) {
      message.warning('请为每个步骤配置参数映射')
      return
    }
    if (!s.completionCondition) {
      message.warning('请为每个步骤填写完成条件')
      return
    }
  }

  submitLoading.value = true
  try {
    const payload = {
      templateName: form.templateName,
      templateIntent: form.templateIntent,
      inputParams: form.inputParams.map(({ __key, ...rest }) => rest),
      steps: form.steps.map(({ __key, paramMapping, ...rest }) => ({
        ...rest,
        paramMapping: paramMapping.map(({ __key, ...m }) => m)
      }))
    }
    if (isEdit.value) {
      await updateBaselineTemplate(editingId.value, { inputParams: payload.inputParams, steps: payload.steps })
    } else {
      await createBaselineTemplate(payload)
    }
    message.success('保存成功')
    formVisible.value = false
    fetchList()
  } finally {
    submitLoading.value = false
  }
}

async function handleEnable(record) {
  await enableBaselineTemplate(record.id)
  message.success('模板已启用')
  fetchList()
}
async function handleDisable(record) {
  await disableBaselineTemplate(record.id)
  message.success('模板已停用')
  fetchList()
}
async function handleDelete(record) {
  await deleteBaselineTemplate(record.id)
  message.success('模板已删除')
  fetchList()
}

const dryRunVisible = ref(false)
const dryRunTarget = ref(null)
const dryRunForm = reactive({ inputParams: {}, deviceByStep: {} })
const dryRunResult = ref(null)
const dryRunLoading = ref(false)
const agentOptions = ref([])

async function openDryRun(record) {
  const detail = (await getBaselineTemplate(record.id)).data
  dryRunTarget.value = detail
  dryRunForm.inputParams = Object.fromEntries((detail.inputParams || []).map(p => [p.name, p.defaultValue ?? '']))
  dryRunForm.deviceByStep = {}
  dryRunResult.value = null
  const agentResp = await listAgents({ agentStatus: 'ENABLED', onlineStatus: 'ONLINE', page: 1, size: 100 })
  agentOptions.value = agentResp.data.content
  dryRunVisible.value = true
}

async function handleStartDryRun() {
  const simulatedDevices = Object.entries(dryRunForm.deviceByStep).map(([stepSeq, agentId]) => ({
    stepSeq: Number(stepSeq), agentId
  }))
  if (simulatedDevices.length < dryRunTarget.value.steps.length) {
    message.warning('请为每个步骤选择模拟设备')
    return
  }
  dryRunLoading.value = true
  try {
    const resp = await dryRunBaselineTemplate(dryRunTarget.value.id, {
      inputParams: dryRunForm.inputParams,
      simulatedDevices
    })
    dryRunResult.value = resp.data
    if (resp.data.result === 'RUNNING') scheduleDryRunPoll()
    else if (resp.data.result === 'SUCCESS') message.success('试运行成功')
    else message.error('试运行未通过')
    fetchList()
  } finally {
    dryRunLoading.value = false
  }
}

let dryRunTimer
function stopDryRunPoll() { clearTimeout(dryRunTimer) }
function scheduleDryRunPoll() {
  stopDryRunPoll()
  dryRunTimer = setTimeout(async () => {
    if (!dryRunVisible.value || !dryRunResult.value) return
    try {
      dryRunResult.value = (await getBaselineDryRun(dryRunTarget.value.id, dryRunResult.value.taskId)).data
      if (dryRunResult.value.result === 'RUNNING') scheduleDryRunPoll()
      else fetchList()
    } catch { message.error('无法获取试运行进度，请查看任务事件'); stopDryRunPoll() }
  }, 1000)
}
async function handleCancelDryRun() {
  stopDryRunPoll()
  dryRunResult.value = (await cancelBaselineDryRun(dryRunTarget.value.id, dryRunResult.value.taskId)).data
  fetchList()
}
watch(dryRunVisible, value => { if (!value) stopDryRunPoll() })
onUnmounted(stopDryRunPoll)

onMounted(() => {
  fetchList()
  fetchTaskDefinitions()
})
</script>
