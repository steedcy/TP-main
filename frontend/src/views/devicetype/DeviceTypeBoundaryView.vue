<template>
  <div>
    <a-tabs v-model:activeKey="activeTab">
      <a-tab-pane key="list" tab="设备类型能力边界">
        <a-table :dataSource="deviceTypes" :columns="listColumns" rowKey="deviceTypeCode" :loading="listLoading">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'action'">
              <a-button size="small" type="link" @click="openDetail(record.deviceTypeCode)">查看详情</a-button>
            </template>
          </template>
        </a-table>
      </a-tab-pane>
      <a-tab-pane key="matrix" tab="能力约束矩阵">
        <a-table :dataSource="matrix" :columns="matrixColumns" :pagination="false" rowKey="deviceTypeCode" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="capCodes.includes(column.dataIndex)">
              <check-outlined v-if="record[column.dataIndex]" style="color: #52c41a" />
              <close-outlined v-else style="color: #d9d9d9" />
            </template>
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <a-drawer v-model:open="detailVisible" title="设备类型详情" width="900px" placement="right">
      <template v-if="detail">
        <a-descriptions :column="1" bordered size="small" style="margin-bottom: 16px">
          <a-descriptions-item label="设备类型编码">{{ detail.deviceTypeCode }}</a-descriptions-item>
          <a-descriptions-item label="设备类型名称">{{ detail.deviceTypeName }}</a-descriptions-item>
          <a-descriptions-item label="已创建实例数">{{ detail.instanceCount }}</a-descriptions-item>
        </a-descriptions>

        <a-form :model="boundaryForm" layout="vertical">
          <a-form-item label="支持能力类型（至少选择1个）">
            <a-checkbox-group v-model:value="boundaryForm.supportedCapabilityTypes" :options="capabilityOptions" />
          </a-form-item>
          <a-form-item label="不支持能力类型">
            <a-tag v-for="c in detail.unsupportedCapabilityTypes" :key="c" color="default">{{ capabilityLabel(c) }}</a-tag>
            <span v-if="!detail.unsupportedCapabilityTypes.length">（无）</span>
          </a-form-item>
          <a-form-item label="类型描述">
            <a-textarea v-model:value="boundaryForm.typeDescription" maxlength="500" :rows="2" />
          </a-form-item>
          <a-form-item label="典型应用场景">
            <a-textarea v-model:value="boundaryForm.typicalScenarios" maxlength="1000" :rows="2" />
          </a-form-item>
          <a-form-item label="能力约束规则">
            <a-textarea v-model:value="boundaryForm.constraintRules" maxlength="1000" :rows="2" />
          </a-form-item>
          <a-form-item>
            <a-button type="primary" :loading="saveLoading" @click="handleSaveBoundary">保存</a-button>
          </a-form-item>
        </a-form>

        <a-divider>标准能力模板列表</a-divider>
        <a-button type="primary" style="margin-bottom: 12px" @click="openTemplateForm(null)">新增能力模板</a-button>
        <a-table :dataSource="templates" :columns="templateColumns" rowKey="templateCode" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'templateStatus'">
              <a-tag :color="record.templateStatus === 'ACTIVE' ? 'green' : 'default'">
                {{ record.templateStatus === 'ACTIVE' ? '启用' : '停用' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button size="small" type="link" @click="openTemplateForm(record)">编辑</a-button>
                <a-button size="small" type="link" @click="handleToggleTemplateStatus(record)">
                  {{ record.templateStatus === 'ACTIVE' ? '停用' : '启用' }}
                </a-button>
                <a-popconfirm title="确认删除该能力模板？" @confirm="handleDeleteTemplate(record)">
                  <a-button size="small" type="link" danger>删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </template>
    </a-drawer>

    <a-modal
      v-model:open="templateFormVisible"
      :title="isEditTemplate ? '编辑能力模板' : '新增能力模板'"
      width="700px"
      @ok="handleSubmitTemplate"
      :confirmLoading="templateSubmitLoading"
    >
      <a-form ref="templateFormRef" :model="templateForm" :rules="templateFormRules" layout="vertical">
        <a-form-item label="模板编码" name="templateCode">
          <a-input v-model:value="templateForm.templateCode" :disabled="isEditTemplate" maxlength="32" placeholder="1~32位，仅字母/数字/下划线" />
        </a-form-item>
        <a-form-item label="模板名称" name="templateName">
          <a-input v-model:value="templateForm.templateName" maxlength="64" />
        </a-form-item>
        <a-form-item label="能力类型" name="capabilityType">
          <a-select v-model:value="templateForm.capabilityType" :disabled="isEditTemplate">
            <a-select-option v-for="c in capabilityOptions" :key="c.value" :value="c.value">{{ c.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="输入参数定义">
          <ParamTableEditor v-model="templateForm.inputParams" mode="input" />
        </a-form-item>
        <a-form-item label="输出参数定义">
          <ParamTableEditor v-model="templateForm.outputParams" mode="output" />
        </a-form-item>
        <a-form-item label="模板说明">
          <a-textarea v-model:value="templateForm.templateDescription" maxlength="500" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { CheckOutlined, CloseOutlined } from '@ant-design/icons-vue'
import {
  listDeviceTypes, getCapabilityBoundary, updateCapabilityBoundary,
  listCapabilityTemplates, createCapabilityTemplate, updateCapabilityTemplate,
  updateCapabilityTemplateStatus, deleteCapabilityTemplate, getCapabilityMatrix
} from '../../api/devicetype'
import { CAPABILITY_TYPES, capabilityLabel } from '../../constants/capability'
import ParamTableEditor from '../../components/ParamTableEditor.vue'

const activeTab = ref('list')
const capabilityOptions = CAPABILITY_TYPES
const capCodes = CAPABILITY_TYPES.map(c => c.value)

const listColumns = [
  { title: '设备类型编码', dataIndex: 'deviceTypeCode' },
  { title: '设备类型名称', dataIndex: 'deviceTypeName' },
  { title: '查看详情', key: 'action' }
]
const deviceTypes = ref([])
const listLoading = ref(false)
async function fetchDeviceTypes() {
  listLoading.value = true
  try {
    const resp = await listDeviceTypes()
    deviceTypes.value = resp.data
  } finally {
    listLoading.value = false
  }
}

const matrixColumns = [
  { title: '设备类型', dataIndex: 'deviceTypeName', fixed: 'left' },
  ...CAPABILITY_TYPES.map(c => ({ title: c.label, dataIndex: c.value, width: 100 }))
]
const matrix = ref([])
async function fetchMatrix() {
  const resp = await getCapabilityMatrix()
  matrix.value = resp.data
}

const detailVisible = ref(false)
const detail = ref(null)
const boundaryForm = reactive({ supportedCapabilityTypes: [], typeDescription: '', constraintRules: '', typicalScenarios: '' })
const saveLoading = ref(false)
const templates = ref([])
const templateColumns = [
  { title: '模板编码', dataIndex: 'templateCode' },
  { title: '模板名称', dataIndex: 'templateName' },
  { title: '能力类型', dataIndex: 'capabilityType', customRender: ({ text }) => capabilityLabel(text) },
  { title: '版本', dataIndex: 'templateVersion' },
  { title: '状态', key: 'templateStatus' },
  { title: '使用数量', dataIndex: 'usageCount' },
  { title: '操作', key: 'action' }
]

async function openDetail(deviceTypeCode) {
  const resp = await getCapabilityBoundary(deviceTypeCode)
  detail.value = resp.data
  Object.assign(boundaryForm, {
    supportedCapabilityTypes: [...resp.data.supportedCapabilityTypes],
    typeDescription: resp.data.typeDescription || '',
    constraintRules: resp.data.constraintRules || '',
    typicalScenarios: resp.data.typicalScenarios || ''
  })
  await fetchTemplates(deviceTypeCode)
  detailVisible.value = true
}

async function fetchTemplates(deviceTypeCode) {
  const resp = await listCapabilityTemplates(deviceTypeCode)
  templates.value = resp.data
}

async function handleSaveBoundary() {
  if (!boundaryForm.supportedCapabilityTypes.length) {
    message.warning('请至少选择1个支持的能力类型')
    return
  }
  saveLoading.value = true
  try {
    const resp = await updateCapabilityBoundary(detail.value.deviceTypeCode, boundaryForm)
    detail.value = resp.data
    message.success('保存成功')
    fetchDeviceTypes()
  } finally {
    saveLoading.value = false
  }
}

const templateFormVisible = ref(false)
const templateSubmitLoading = ref(false)
const isEditTemplate = ref(false)
const templateFormRef = ref(null)
let paramKeySeq = 0
const withKeys = (params) => (params || []).map(p => ({ ...p, __key: `k${paramKeySeq++}` }))
const emptyTemplateForm = () => ({
  templateCode: '', templateName: '', capabilityType: undefined,
  inputParams: [], outputParams: [], templateDescription: ''
})
const templateForm = reactive(emptyTemplateForm())
const templateFormRules = {
  templateCode: [
    { required: true, message: '请输入模板编码' },
    { pattern: /^[A-Za-z0-9_]{1,32}$/, message: '仅允许字母、数字、下划线，长度1~32位' }
  ],
  templateName: [{ required: true, message: '请输入模板名称' }],
  capabilityType: [{ required: true, message: '请选择能力类型' }]
}

function openTemplateForm(record) {
  isEditTemplate.value = !!record
  if (record) {
    Object.assign(templateForm, {
      templateCode: record.templateCode, templateName: record.templateName,
      capabilityType: record.capabilityType,
      inputParams: withKeys(record.inputParams), outputParams: withKeys(record.outputParams),
      templateDescription: record.templateDescription
    })
  } else {
    Object.assign(templateForm, emptyTemplateForm())
  }
  templateFormVisible.value = true
}

async function handleSubmitTemplate() {
  try {
    await templateFormRef.value.validate()
  } catch {
    return
  }
  if (!templateForm.inputParams.length) {
    message.warning('请定义至少1个输入参数')
    return
  }
  if (!templateForm.outputParams.length) {
    message.warning('请定义至少1个输出参数')
    return
  }
  templateSubmitLoading.value = true
  try {
    const payload = {
      ...templateForm,
      inputParams: templateForm.inputParams.map(({ __key, ...rest }) => rest),
      outputParams: templateForm.outputParams.map(({ __key, ...rest }) => rest)
    }
    if (isEditTemplate.value) {
      await updateCapabilityTemplate(detail.value.deviceTypeCode, templateForm.templateCode, payload)
    } else {
      await createCapabilityTemplate(detail.value.deviceTypeCode, payload)
    }
    message.success('保存成功')
    templateFormVisible.value = false
    fetchTemplates(detail.value.deviceTypeCode)
    fetchDeviceTypes()
  } finally {
    templateSubmitLoading.value = false
  }
}

async function handleToggleTemplateStatus(record) {
  const newStatus = record.templateStatus === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  await updateCapabilityTemplateStatus(detail.value.deviceTypeCode, record.templateCode, newStatus)
  message.success('操作成功')
  fetchTemplates(detail.value.deviceTypeCode)
}

async function handleDeleteTemplate(record) {
  await deleteCapabilityTemplate(detail.value.deviceTypeCode, record.templateCode)
  message.success('删除成功')
  fetchTemplates(detail.value.deviceTypeCode)
}

onMounted(() => {
  fetchDeviceTypes()
  fetchMatrix()
})
</script>
