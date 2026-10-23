<template>
  <div>
    <a-space style="margin-bottom: 16px">
      <a-select v-model:value="filters.deviceTypeCode" style="width: 180px" placeholder="按设备类型筛选" allow-clear @change="fetchList">
        <a-select-option v-for="t in deviceTypes" :key="t.value" :value="t.value">{{ t.label }}</a-select-option>
      </a-select>
      <a-input v-model:value="filters.keyword" placeholder="按名称/编码检索" style="width: 200px" @pressEnter="fetchList" allow-clear @change="fetchList" />
      <a-button type="primary" @click="openCreate">新增设备</a-button>
    </a-space>

    <a-table :dataSource="list" :columns="columns" rowKey="id" :pagination="pagination" @change="handleTableChange">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'deviceTypeCode'">
          {{ deviceTypeLabel(record.deviceTypeCode) }}
        </template>
        <template v-else-if="column.key === 'isSimulator'">
          <a-tag :color="record.isSimulator ? 'blue' : 'default'">{{ record.isSimulator ? '仿真体' : '真实设备' }}</a-tag>
        </template>
        <template v-else-if="column.key === 'connectionTestStatus'">
          <a-tag :color="{ PASSED: 'green', FAILED: 'red', UNTESTED: 'default' }[record.connectionTestStatus]">
            {{ { PASSED: '通过', FAILED: '失败', UNTESTED: '未测试' }[record.connectionTestStatus] }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'deviceStatus'">
          <a-tag :color="record.deviceStatus === 'ACTIVE' ? 'green' : 'default'">
            {{ record.deviceStatus === 'ACTIVE' ? '启用' : '停用' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space wrap>
            <a-button size="small" @click="openEdit(record)">编辑</a-button>
            <a-button size="small" @click="$router.push(`/devices/${record.deviceCode}/capabilities`)">能力管理</a-button>
            <a-button size="small" @click="handleTestConnection(record)">连接测试</a-button>
            <a-button
              size="small" type="primary"
              :disabled="record.connectionTestStatus !== 'PASSED' || record.deviceStatus !== 'ACTIVE'"
              @click="handleCreateAgent(record)"
            >
              创建启用代理
            </a-button>
            <a-popconfirm
              :title="record.deviceStatus === 'ACTIVE' ? '停用设备将同步停用其代理，确认停用？' : '确认启用该设备？'"
              @confirm="handleToggleStatus(record)"
            >
              <a-button size="small" danger>{{ record.deviceStatus === 'ACTIVE' ? '停用' : '启用' }}</a-button>
            </a-popconfirm>
            <a-popconfirm title="删除后不可恢复，确认删除该设备？" @confirm="handleDelete(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="formVisible"
      :title="isEdit ? '编辑设备' : '新增设备'"
      @ok="handleSubmit"
      :confirmLoading="submitLoading"
      width="600px"
    >
      <a-form ref="formRef" :model="form" :rules="formRules" layout="vertical">
        <a-form-item label="设备编码" name="deviceCode">
          <a-input v-model:value="form.deviceCode" :disabled="isEdit" maxlength="32" placeholder="1~32位，仅字母/数字/下划线/短横线" />
        </a-form-item>
        <a-form-item label="设备名称" name="deviceName">
          <a-input v-model:value="form.deviceName" maxlength="64" />
        </a-form-item>
        <a-form-item label="设备类型" name="deviceTypeCode">
          <a-select v-model:value="form.deviceTypeCode" :disabled="isEdit">
            <a-select-option v-for="t in deviceTypes" :key="t.value" :value="t.value">{{ t.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="虚实属性" name="isSimulator" v-if="!isEdit">
          <a-radio-group v-model:value="form.isSimulator">
            <a-radio :value="false">真实设备</a-radio>
            <a-radio :value="true">仿真体</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item
          label="所模拟的设备类型" name="simulatedDeviceType"
          v-if="!isEdit && form.isSimulator"
        >
          <a-select v-model:value="form.simulatedDeviceType" placeholder="仿真体须选择所模拟的设备类型">
            <a-select-option v-for="t in deviceTypes.filter(d => d.value !== 'SIMULATOR')" :key="t.value" :value="t.value">
              {{ t.label }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="所属区域" name="areaCode">
          <a-input v-model:value="form.areaCode" placeholder="如：T2-B区候机厅" />
        </a-form-item>
        <a-form-item label="位置坐标">
          <a-space>
            <a-input-number v-model:value="form.positionX" placeholder="X" style="width: 140px" />
            <a-input-number v-model:value="form.positionY" placeholder="Y" style="width: 140px" />
          </a-space>
        </a-form-item>
        <a-form-item label="接入接口地址" name="accessEndpoint">
          <a-input v-model:value="form.accessEndpoint" placeholder="设备接口地址" />
        </a-form-item>
        <a-form-item label="接入凭据标识" name="accessCredentialRef">
          <a-input-password v-model:value="form.accessCredentialRef" :placeholder="isEdit ? '留空则不修改（当前：' + form.accessCredentialRefMasked + '）' : '凭据标识'" />
        </a-form-item>
        <a-form-item label="状态上报周期（5~60秒）" name="statusReportInterval">
          <a-input-number v-model:value="form.statusReportInterval" :min="5" :max="60" />
        </a-form-item>
        <a-form-item label="备注" name="remark">
          <a-textarea v-model:value="form.remark" maxlength="200" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  listDevices, createDevice, updateDevice, testConnection,
  updateDeviceStatus, deleteDevice, createAgent
} from '../../api/device'
import { DEVICE_TYPES as deviceTypes, deviceTypeLabel } from '../../constants/capability'

const list = ref([])
const filters = reactive({ deviceTypeCode: undefined, keyword: '' })
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const columns = [
  { title: '设备编码', dataIndex: 'deviceCode' },
  { title: '设备名称', dataIndex: 'deviceName' },
  { title: '设备类型', key: 'deviceTypeCode' },
  { title: '虚实属性', key: 'isSimulator' },
  { title: '所属区域', dataIndex: 'areaCode' },
  { title: '连接测试', key: 'connectionTestStatus' },
  { title: '设备状态', key: 'deviceStatus' },
  { title: '操作', key: 'action', width: 360 }
]

const formVisible = ref(false)
const submitLoading = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const emptyForm = () => ({
  deviceCode: '', deviceName: '', deviceTypeCode: 'SMART_DISPLAY',
  isSimulator: false, simulatedDeviceType: undefined,
  areaCode: '', positionX: undefined, positionY: undefined,
  accessEndpoint: '', accessCredentialRef: '', accessCredentialRefMasked: '',
  statusReportInterval: 15, remark: ''
})
const form = reactive(emptyForm())

// 字段约束对应5.2.1界面元素与附录B 6.3.1节
const formRules = {
  deviceCode: [
    { required: true, message: '请输入设备编码' },
    { pattern: /^[A-Za-z0-9_-]{1,32}$/, message: '仅允许字母、数字、下划线和短横线，长度1~32位' }
  ],
  deviceName: [{ required: true, message: '请输入设备名称' }, { max: 64, message: '最长64位' }],
  deviceTypeCode: [{ required: true, message: '请选择设备类型' }],
  areaCode: [{ required: true, message: '请选择所属区域' }],
  accessEndpoint: [{ required: true, message: '请输入接入接口地址' }],
  statusReportInterval: [{ required: true, message: '请输入状态上报周期' }]
}
// 新增时凭据标识必填，编辑时留空表示不修改（对应5.2.1业务规则8），故不在formRules中做静态required校验


async function fetchList() {
  const resp = await listDevices({
    deviceTypeCode: filters.deviceTypeCode, keyword: filters.keyword,
    page: pagination.current, size: pagination.pageSize
  })
  list.value = resp.data.content
  pagination.total = resp.data.totalElements
}

function handleTableChange(pag) {
  pagination.current = pag.current
  fetchList()
}

function openCreate() {
  isEdit.value = false
  Object.assign(form, emptyForm())
  formVisible.value = true
}

function openEdit(record) {
  isEdit.value = true
  Object.assign(form, {
    deviceCode: record.deviceCode, deviceName: record.deviceName, deviceTypeCode: record.deviceTypeCode,
    isSimulator: record.isSimulator, simulatedDeviceType: record.simulatedDeviceType,
    areaCode: record.areaCode, positionX: record.positionX, positionY: record.positionY,
    accessEndpoint: record.accessEndpoint, accessCredentialRef: '',
    accessCredentialRefMasked: record.accessCredentialRefMasked,
    statusReportInterval: record.statusReportInterval, remark: record.remark
  })
  formVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  if (!isEdit.value && !form.accessCredentialRef) {
    message.warning('请输入接入凭据标识')
    return
  }
  if (!isEdit.value && form.isSimulator && !form.simulatedDeviceType) {
    message.warning('仿真体须选择所模拟的设备类型')
    return
  }
  if (form.positionX === undefined || form.positionY === undefined) {
    message.warning('请输入位置坐标')
    return
  }
  submitLoading.value = true
  try {
    if (isEdit.value) {
      // 出于安全考虑系统不回显凭据原值（5.2.1业务规则8），编辑时留空表示不修改凭据，
      // 只有确实需要更换凭据时才填写
      await updateDevice(form.deviceCode, form)
    } else {
      await createDevice(form)
    }
    message.success(isEdit.value ? '设备已更新' : '设备创建成功')
    formVisible.value = false
    fetchList()
  } finally {
    submitLoading.value = false
  }
}

async function handleTestConnection(record) {
  const resp = await testConnection(record.deviceCode)
  if (resp.data.result === 'PASSED') {
    message.success('连接测试通过')
  } else {
    message.error('连接测试失败：' + (resp.data.failReason || '未知原因'))
  }
  fetchList()
}

async function handleCreateAgent(record) {
  await createAgent(record.deviceCode)
  message.success('设备代理创建成功')
  fetchList()
}

async function handleToggleStatus(record) {
  const newStatus = record.deviceStatus === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  await updateDeviceStatus(record.deviceCode, newStatus)
  message.success('操作成功')
  fetchList()
}

async function handleDelete(record) {
  await deleteDevice(record.deviceCode)
  message.success('设备已删除')
  fetchList()
}

onMounted(fetchList)
</script>
