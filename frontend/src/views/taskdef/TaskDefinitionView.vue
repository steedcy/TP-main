<template>
  <div>
    <a-alert message="预置三类核心任务族（超规行李处置/特殊旅客服务/航班变更应对）不可删除，仅可编辑场景参数与约束或停用" type="warning" style="margin-bottom: 16px" />
    <a-button type="primary" style="margin-bottom: 16px" @click="openForm(null)">新增任务定义</a-button>

    <a-table :dataSource="definitions" :columns="columns" rowKey="id" :loading="listLoading">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'isPreset'">
          <a-tag :color="record.isPreset ? 'blue' : 'default'">{{ record.isPreset ? '预置' : '扩展' }}</a-tag>
        </template>
        <template v-else-if="column.key === 'definitionStatus'">
          <a-tag :color="record.definitionStatus === 'ENABLED' ? 'green' : 'default'">
            {{ record.definitionStatus === 'ENABLED' ? '已启用' : '已停用' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space wrap>
            <a-button size="small" @click="openForm(record)">编辑</a-button>
            <a-popconfirm v-if="record.definitionStatus === 'ENABLED'" title="停用后提交任务页不再展示该任务族，已有任务不受影响，确认停用？" @confirm="handleDisable(record)">
              <a-button size="small" danger>停用</a-button>
            </a-popconfirm>
            <a-button v-else size="small" type="primary" @click="handleEnable(record)">启用</a-button>
            <a-tooltip v-if="record.isPreset" title="预置任务族不可删除">
              <a-button size="small" danger disabled>删除</a-button>
            </a-tooltip>
            <a-popconfirm v-else title="确认删除该任务定义？" @confirm="handleDelete(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="formVisible"
      :title="isEdit ? '编辑任务定义' : '新增任务定义'"
      width="800px"
      @ok="handleSubmit"
      :confirmLoading="submitLoading"
    >
      <a-form ref="formRef" :model="form" :rules="formRules" layout="vertical">
        <a-form-item label="任务名称（系统内唯一，1~64位）" name="taskName">
          <a-input v-model:value="form.taskName" :disabled="isEdit" maxlength="64" />
        </a-form-item>
        <a-form-item label="自然语言目标模板（1~500位，作为提交任务时的目标样例）" name="goalTemplate">
          <a-textarea v-model:value="form.goalTemplate" :rows="2" maxlength="500" show-count />
        </a-form-item>
        <a-form-item label="场景参数定义">
          <ParamTableEditor v-model="form.sceneParams" mode="input" />
        </a-form-item>
        <a-form-item label="可用能力类型（取值来自预置8类能力类型）">
          <a-checkbox-group v-model:value="form.availableCapabilityTypes">
            <a-checkbox v-for="c in CAPABILITY_TYPES" :key="c.value" :value="c.value">{{ c.label }}</a-checkbox>
          </a-checkbox-group>
        </a-form-item>
        <a-form-item label="约束条件（描述该任务族的业务约束，参与5.4.4约束校验的能力范围维度）">
          <a-textarea v-model:value="form.constraintDescription" :rows="2" />
        </a-form-item>
        <a-form-item label="预期完成条件（描述任务完成判定依据）" name="completionCondition">
          <a-textarea v-model:value="form.completionCondition" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  listTaskDefinitions, getTaskDefinition, createTaskDefinition, updateTaskDefinition,
  enableTaskDefinition, disableTaskDefinition, deleteTaskDefinition
} from '../../api/taskDefinition'
import { CAPABILITY_TYPES } from '../../constants/capability'
import ParamTableEditor from '../../components/ParamTableEditor.vue'

const definitions = ref([])
const listLoading = ref(false)
const columns = [
  { title: '任务名称', dataIndex: 'taskName' },
  { title: '目标模板', dataIndex: 'goalTemplate', ellipsis: true },
  { title: '类型', key: 'isPreset', width: 80 },
  { title: '状态', key: 'definitionStatus', width: 90 },
  { title: '操作', key: 'action', width: 280 }
]

async function fetchList() {
  listLoading.value = true
  try {
    const resp = await listTaskDefinitions()
    definitions.value = resp.data
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
const withParamKeys = (params) => (params || []).map(p => ({ ...p, __key: `p${paramKeySeq++}` }))
const emptyForm = () => ({
  taskName: '', goalTemplate: '', sceneParams: [], availableCapabilityTypes: [],
  constraintDescription: '', completionCondition: ''
})
const form = reactive(emptyForm())
const formRules = {
  taskName: [{ required: true, message: '请输入任务名称' }, { max: 64, message: '最长64位' }],
  goalTemplate: [{ required: true, message: '请输入自然语言目标模板' }, { max: 500, message: '最长500位' }],
  completionCondition: [{ required: true, message: '请输入预期完成条件' }]
}

async function openForm(record) {
  isEdit.value = !!record
  editingId.value = record?.id || null
  if (record) {
    const detail = (await getTaskDefinition(record.id)).data
    Object.assign(form, {
      taskName: detail.taskName,
      goalTemplate: detail.goalTemplate,
      sceneParams: withParamKeys(detail.sceneParams),
      availableCapabilityTypes: detail.availableCapabilityTypes || [],
      constraintDescription: detail.constraintDescription || '',
      completionCondition: detail.completionCondition
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
  if (!form.sceneParams.length) {
    message.warning('请定义至少1个场景参数')
    return
  }
  if (!form.availableCapabilityTypes.length) {
    message.warning('请选择至少1个可用能力类型')
    return
  }

  submitLoading.value = true
  try {
    const payload = {
      goalTemplate: form.goalTemplate,
      sceneParams: form.sceneParams.map(({ __key, ...rest }) => rest),
      availableCapabilityTypes: form.availableCapabilityTypes,
      constraintDescription: form.constraintDescription,
      completionCondition: form.completionCondition
    }
    if (isEdit.value) {
      await updateTaskDefinition(editingId.value, payload)
    } else {
      await createTaskDefinition({ ...payload, taskName: form.taskName })
    }
    message.success('保存成功')
    formVisible.value = false
    fetchList()
  } finally {
    submitLoading.value = false
  }
}

async function handleEnable(record) {
  await enableTaskDefinition(record.id)
  message.success('已启用')
  fetchList()
}
async function handleDisable(record) {
  await disableTaskDefinition(record.id)
  message.success('已停用')
  fetchList()
}
async function handleDelete(record) {
  await deleteTaskDefinition(record.id)
  message.success('已删除')
  fetchList()
}

onMounted(fetchList)
</script>
