<template>
  <div>
    <a-page-header :title="`能力管理 - ${deviceCode}`" @back="$router.push('/devices')" />
    <a-space style="margin-bottom: 16px">
      <a-button type="primary" @click="openForm(null)">新增能力</a-button>
      <a-select
        v-if="availableTemplates.length"
        placeholder="基于标准能力模板新增"
        style="width: 240px"
        @change="openFormFromTemplate"
      >
        <a-select-option v-for="t in availableTemplates" :key="t.templateCode" :value="t.templateCode">
          {{ t.templateName }}（{{ capabilityLabel(t.capabilityType) }}）
        </a-select-option>
      </a-select>
    </a-space>

    <a-table :dataSource="list" :columns="columns" rowKey="capabilityCode">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'capabilityType'">
          {{ capabilityLabel(record.capabilityType) }}
        </template>
        <template v-else-if="column.key === 'capabilityStatus'">
          <a-tag :color="statusColor(record.capabilityStatus)">{{ statusLabel(record.capabilityStatus) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space wrap>
            <a-button size="small" @click="openForm(record)">编辑</a-button>
            <a-button size="small" @click="handleTest(record)">模拟调用测试</a-button>
            <a-button
              size="small" type="primary"
              :disabled="!['TESTED_PASSED', 'DISABLED'].includes(record.capabilityStatus)"
              v-if="record.capabilityStatus !== 'ENABLED'"
              @click="handleUpdateStatus(record, 'ENABLED')"
            >
              启用
            </a-button>
            <a-popconfirm v-else title="停用后立即退出规划可用能力集合，确认停用？" @confirm="handleUpdateStatus(record, 'DISABLED')">
              <a-button size="small" danger>停用</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="formVisible"
      :title="isEdit ? '编辑能力' : '新增能力'"
      width="800px"
      @ok="handleSubmit"
      :confirmLoading="submitLoading"
    >
      <a-form ref="formRef" :model="form" :rules="formRules" layout="vertical">
        <a-form-item label="能力编码" name="capabilityCode">
          <a-input v-model:value="form.capabilityCode" :disabled="isEdit" maxlength="32" placeholder="同一设备内唯一，1~32位" />
        </a-form-item>
        <a-form-item label="能力名称" name="capabilityName">
          <a-input v-model:value="form.capabilityName" maxlength="64" />
        </a-form-item>
        <a-form-item label="能力类型" name="capabilityType">
          <a-select v-model:value="form.capabilityType" :disabled="isEdit" placeholder="仅展示所属设备类型支持的能力类型">
            <a-select-option v-for="c in supportedCapabilities" :key="c" :value="c">{{ capabilityLabel(c) }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="输入参数">
          <ParamTableEditor v-model="form.inputParams" mode="input" />
        </a-form-item>
        <a-form-item label="输出参数">
          <ParamTableEditor v-model="form.outputParams" mode="output" />
        </a-form-item>
        <a-form-item label="适用条件">
          <a-textarea v-model:value="form.applicableCondition" :rows="2" placeholder="如所属区域、设备工作状态要求" />
        </a-form-item>
        <a-form-item label="能力说明">
          <a-textarea v-model:value="form.capabilityDescription" maxlength="500" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="testResultVisible" title="模拟调用测试结果" :footer="null">
      <a-descriptions :column="1" bordered size="small">
        <a-descriptions-item label="测试结果">
          <a-tag :color="testResultData.capabilityStatus === 'TESTED_PASSED' ? 'green' : 'red'">
            {{ testResultData.capabilityStatus === 'TESTED_PASSED' ? '通过' : '失败' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="详情">{{ testResultData.testResult }}</a-descriptions-item>
        <a-descriptions-item label="测试时间">{{ testResultData.lastTestAt }}</a-descriptions-item>
        <a-descriptions-item label="耗时">{{ testResultData.testDurationMs }} ms</a-descriptions-item>
        <a-descriptions-item label="调用请求"><pre style="white-space: pre-wrap; margin: 0">{{ testResultData.testRequest || '—' }}</pre></a-descriptions-item>
        <a-descriptions-item label="设备响应"><pre style="white-space: pre-wrap; margin: 0">{{ testResultData.testResponse || '—' }}</pre></a-descriptions-item>
      </a-descriptions>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  listDeviceCapabilities, createDeviceCapability, updateDeviceCapability,
  testDeviceCapability, updateDeviceCapabilityStatus,
  listCapabilityTemplates, getCapabilityBoundary
} from '../../api/devicetype'
import { getDevice } from '../../api/device'
import { capabilityLabel } from '../../constants/capability'
import ParamTableEditor from '../../components/ParamTableEditor.vue'

const route = useRoute()
const deviceCode = route.params.deviceCode

const list = ref([])
const supportedCapabilities = ref([])
const availableTemplates = ref([])
const allTemplates = ref([])

const columns = [
  { title: '能力编码', dataIndex: 'capabilityCode' },
  { title: '能力名称', dataIndex: 'capabilityName' },
  { title: '能力类型', key: 'capabilityType' },
  { title: '可用状态', key: 'capabilityStatus' },
  { title: '最近测试时间', dataIndex: 'lastTestAt' },
  { title: '操作', key: 'action', width: 320 }
]

function statusLabel(s) {
  return { UNTESTED: '未测试', TESTED_PASSED: '测试通过', TESTED_FAILED: '测试失败', ENABLED: '已启用', DISABLED: '已停用' }[s] || s
}
function statusColor(s) {
  return { UNTESTED: 'default', TESTED_PASSED: 'blue', TESTED_FAILED: 'red', ENABLED: 'green', DISABLED: 'default' }[s]
}

async function fetchList() {
  const resp = await listDeviceCapabilities(deviceCode)
  list.value = resp.data
}

async function fetchSupportedCapabilities() {
  const device = (await getDevice(deviceCode)).data
  // 仿真体额外继承所模拟设备类型的能力（对应5.2.4A业务规则4），下拉候选由后端边界数据推导，
  // 前端仅做展示层过滤：直接用设备类型自身边界 + （若为仿真体）模拟类型边界的并集
  const boundary = (await getCapabilityBoundary(device.deviceTypeCode)).data
  let supported = [...boundary.supportedCapabilityTypes]
  if (device.isSimulator && device.simulatedDeviceType) {
    const simBoundary = (await getCapabilityBoundary(device.simulatedDeviceType)).data
    supported = [...new Set([...supported, ...simBoundary.supportedCapabilityTypes])]
  }
  supportedCapabilities.value = supported

  const templates = (await listCapabilityTemplates(device.deviceTypeCode)).data
  allTemplates.value = templates
  availableTemplates.value = templates.filter(t => t.templateStatus === 'ACTIVE')
}

const formVisible = ref(false)
const submitLoading = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
let paramKeySeq = 0
const withKeys = (params) => (params || []).map(p => ({ ...p, __key: `k${paramKeySeq++}` }))
const emptyForm = () => ({
  capabilityCode: '', capabilityName: '', capabilityType: undefined,
  inputParams: [], outputParams: [], applicableCondition: '', capabilityDescription: '', templateId: null
})
const form = reactive(emptyForm())
const formRules = {
  capabilityCode: [{ required: true, message: '请输入能力编码' }, { max: 32, message: '最长32位' }],
  capabilityName: [{ required: true, message: '请输入能力名称' }],
  capabilityType: [{ required: true, message: '请选择能力类型' }]
}

function openForm(record) {
  isEdit.value = !!record
  if (record) {
    Object.assign(form, {
      capabilityCode: record.capabilityCode, capabilityName: record.capabilityName,
      capabilityType: record.capabilityType,
      inputParams: withKeys(record.inputParams), outputParams: withKeys(record.outputParams),
      applicableCondition: record.applicableConditions, capabilityDescription: record.capabilityDescription,
      templateId: null
    })
  } else {
    Object.assign(form, emptyForm())
  }
  formVisible.value = true
}

function openFormFromTemplate(templateCode) {
  const t = allTemplates.value.find(x => x.templateCode === templateCode)
  if (!t) return
  isEdit.value = false
  Object.assign(form, {
    capabilityCode: '', capabilityName: t.templateName, capabilityType: t.capabilityType,
    inputParams: withKeys(t.inputParams), outputParams: withKeys(t.outputParams),
    applicableCondition: '', capabilityDescription: t.templateDescription, templateId: t.id
  })
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
  if (!form.outputParams.length) {
    message.warning('请定义至少1个输出参数')
    return
  }
  submitLoading.value = true
  try {
    const strippedParams = {
      inputParams: form.inputParams.map(({ __key, ...rest }) => rest),
      outputParams: form.outputParams.map(({ __key, ...rest }) => rest)
    }
    if (isEdit.value) {
      // 后端 UpdateDeviceCapabilityRequest 白名单：编码/类型不可改
      await updateDeviceCapability(deviceCode, form.capabilityCode, {
        capabilityName: form.capabilityName,
        applicableCondition: form.applicableCondition,
        capabilityDescription: form.capabilityDescription,
        ...strippedParams
      })
    } else {
      await createDeviceCapability(deviceCode, {
        capabilityCode: form.capabilityCode,
        capabilityName: form.capabilityName,
        capabilityType: form.capabilityType,
        templateId: form.templateId,
        ...strippedParams,
        applicableCondition: form.applicableCondition,
        capabilityDescription: form.capabilityDescription
      })
    }
    message.success('保存成功')
    formVisible.value = false
    fetchList()
  } finally {
    submitLoading.value = false
  }
}

const testResultVisible = ref(false)
const testResultData = ref({})
async function handleTest(record) {
  const resp = await testDeviceCapability(deviceCode, record.capabilityCode)
  testResultData.value = resp.data
  testResultVisible.value = true
  fetchList()
}

async function handleUpdateStatus(record, status) {
  await updateDeviceCapabilityStatus(deviceCode, record.capabilityCode, status)
  message.success('操作成功')
  fetchList()
}

onMounted(() => {
  fetchList()
  fetchSupportedCapabilities()
})
</script>
