<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>仿真场景控制</h2>
      <p>启动或停止仿真体、设置执行场景，并查看最近的设备事件与命令记录。</p>
      </div>
      <a-button @click="load" :loading="loading">刷新</a-button>
    </div>

    <a-alert
      message="停止仿真体会暂停心跳并拒绝新的业务命令；运行进程仍保留，以便管理端恢复。故障场景会影响后续任务，演示结束后可切回成功场景。"
      type="info"
      show-icon
      style="margin-bottom: 16px"
    />

    <a-card title="端到端演示任务" style="margin-bottom: 16px">
      <a-row :gutter="16">
        <a-col v-for="demo in demos" :key="demo.key" :span="8">
          <div class="demo-card">
            <strong>{{ demo.title }}</strong>
            <p>{{ demo.description }}</p>
            <a-button type="primary" :loading="submitting === demo.key" :disabled="!hasOnlineTypes(demo.requiredTypes)" @click="submitDemo(demo)">
              提交演示任务
            </a-button>
            <small v-if="!hasOnlineTypes(demo.requiredTypes)">请先接入并启用所需类型的在线仿真体</small>
          </div>
        </a-col>
      </a-row>
    </a-card>

    <a-table :columns="columns" :data-source="simulators" :loading="loading" row-key="deviceCode" :pagination="false">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'type'">
          {{ typeLabels[record.simulatedDeviceType] || record.simulatedDeviceType }}
        </template>
        <template v-else-if="column.key === 'state'">
          <a-tag :color="record.onlineStatus === 'ONLINE' ? 'green' : 'default'">{{ record.onlineStatus === 'ONLINE' ? '在线' : '离线' }}</a-tag>
          <a-tag>{{ record.workStatus === 'BUSY' ? '执行中' : '空闲' }}</a-tag>
        </template>
        <template v-else-if="column.key === 'scenario'">
          <a-select
            :value="record.scenarioResult || 'SUCCESS'"
            style="width: 150px"
            :options="scenarioOptions(record.simulatedDeviceType)"
            @change="value => changeScenario(record, value)"
          />
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button size="small" :disabled="!record.agentCode || record.onlineStatus === 'ONLINE'" @click="changeOnline(record, 'ONLINE')">启动仿真体</a-button>
            <a-button size="small" danger :disabled="!record.agentCode || record.onlineStatus !== 'ONLINE'" @click="changeOnline(record, 'OFFLINE')">停止仿真体</a-button>
            <a-button size="small" @click="showRecords(record)">事件 / 命令</a-button>
          </a-space>
        </template>
        <template v-else-if="column.key === 'reportedAt'">
          {{ formatTime(record.lastReportedAt) }}
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="recordsOpen" :title="`${selected?.deviceName || ''} · 最近记录`" width="900px" :footer="null">
      <a-tabs>
        <a-tab-pane key="events" tab="设备事件">
          <a-table :columns="eventColumns" :data-source="events" row-key="id" size="small" :pagination="{ pageSize: 8 }" />
        </a-tab-pane>
        <a-tab-pane key="commands" tab="命令记录">
          <a-table :columns="commandColumns" :data-source="commands" row-key="id" size="small" :pagination="{ pageSize: 8 }" />
        </a-tab-pane>
      </a-tabs>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  listSimulators, setSimulatorOnline, setSimulatorScenario,
  listSimulatorEvents, listSimulatorCommands
} from '../../api/simulator'
import { submitTask } from '../../api/task'


const simulators = ref([])
const loading = ref(false)
const recordsOpen = ref(false)
const selected = ref(null)
const events = ref([])
const commands = ref([])
const submitting = ref('')
let refreshTimer

const typeLabels = {
  SMART_DISPLAY: '智慧航显',
  BAGGAGE_SCANNER: '行李测量设备',
  FLIGHT_DELAY_BOARD: '航延屏',
  MOBILE_ROBOT: '移动服务机器人'
}
const scenarioLabels = { SUCCESS: '正常成功', FAILED: '设备错误', TIMEOUT: '执行超时', NO_OBJECT: '无行李对象', LOST_TARGET: '目标丢失' }
const demos = [
  {
    key: 'flight', title: '航班变更与旅客引导',
    description: '航延屏发布变更，航显展示引导，机器人通知或导航。',
    requiredTypes: ['FLIGHT_DELAY_BOARD', 'SMART_DISPLAY', 'MOBILE_ROBOT'],
    taskGoal: '航班CA1234延误30分钟，请在T2候机区发布航班变更信息，并引导旅客前往GATE_A05。'
  },
  {
    key: 'baggage', title: '超规行李处置',
    description: '测量行李尺寸重量，并对超规结果生成告警。',
    requiredTypes: ['BAGGAGE_SCANNER'],
    taskGoal: '请测量当前行李的长宽高和重量；如果超出机场行李标准，请上报超规告警。'
  },
  {
    key: 'escort', title: '特殊旅客陪同',
    description: '航显发布会合提示，机器人陪同旅客到登机口。',
    requiredTypes: ['SMART_DISPLAY', 'MOBILE_ROBOT'],
    taskGoal: '请在T2值机区显示特殊旅客会合提示，并安排服务机器人陪同旅客前往GATE_A05。'
  }
]
const columns = [
  { title: '设备编码', dataIndex: 'deviceCode', key: 'deviceCode' },
  { title: '仿真设备', dataIndex: 'deviceName', key: 'deviceName' },
  { title: '模拟类型', key: 'type' },
  { title: '设备状态', key: 'state' },
  { title: '执行场景', key: 'scenario' },
  { title: '最后上报', key: 'reportedAt' },
  { title: '操作', key: 'actions', width: 300 }
]
const eventColumns = [
  { title: '时间', dataIndex: 'occurredAt', key: 'occurredAt' },
  { title: '事件', dataIndex: 'eventType', key: 'eventType' },
  { title: '来源', dataIndex: 'trigger', key: 'trigger' },
  { title: '原因码', dataIndex: 'reasonCode', key: 'reasonCode' },
  { title: '说明', dataIndex: 'detailSummary', key: 'detailSummary' }
]
const commandColumns = [
  { title: '命令编号', dataIndex: 'commandId', key: 'commandId' },
  { title: '命令类型', dataIndex: 'commandType', key: 'commandType' },
  { title: '能力', dataIndex: 'capabilityType', key: 'capabilityType' },
  { title: '任务', dataIndex: 'taskId', key: 'taskId' },
  { title: '状态', dataIndex: 'commandStatus', key: 'commandStatus' },
  { title: '更新时间', dataIndex: 'updatedAt', key: 'updatedAt' }
]

function scenarioOptions(type) {
  const values = type === 'BAGGAGE_SCANNER'
    ? ['SUCCESS', 'FAILED', 'TIMEOUT', 'NO_OBJECT']
    : type === 'MOBILE_ROBOT'
      ? ['SUCCESS', 'FAILED', 'TIMEOUT', 'LOST_TARGET']
      : ['SUCCESS', 'FAILED', 'TIMEOUT']
  return values.map(value => ({ value, label: scenarioLabels[value] }))
}

async function load() {
  loading.value = true
  try { simulators.value = (await listSimulators()).data || [] }
  finally { loading.value = false }
}

function hasOnlineTypes(requiredTypes) {
  return requiredTypes.every(type => simulators.value.some(device =>
    device.simulatedDeviceType === type && device.agentStatus === 'ENABLED' && device.onlineStatus === 'ONLINE'
  ))
}

async function submitDemo(demo) {
  submitting.value = demo.key
  try {
    const response = await submitTask({ taskGoal: demo.taskGoal })
    const task = response.data
    message.success(`已提交演示任务${task?.taskCode ? `：${task.taskCode}` : ''}`)
  } finally { submitting.value = '' }
}

async function changeOnline(record, value) {
  await setSimulatorOnline(record.deviceCode, value)
  message.success(value === 'ONLINE' ? '仿真体已启动' : '仿真体已停止')
  await load()
}

async function changeScenario(record, value) {
  await setSimulatorScenario(record.deviceCode, value)
  message.success(`仿真场景已设为${scenarioLabels[value]}`)
  await load()
}

async function showRecords(record) {
  selected.value = record
  recordsOpen.value = true
  const [eventResult, commandResult] = await Promise.all([
    listSimulatorEvents(record.deviceCode), listSimulatorCommands(record.deviceCode)
  ])
  events.value = eventResult.data || []
  commands.value = commandResult.data || []
}

function formatTime(value) { return value ? new Date(value).toLocaleString() : '—' }

onMounted(() => {
  load()
  refreshTimer = setInterval(load, 5000)
})
onUnmounted(() => clearInterval(refreshTimer))
</script>

<style scoped>
.page-heading { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-heading h2 { margin: 0 0 6px; }
.page-heading p { margin: 0; color: #777; }
.demo-card { min-height: 150px; padding: 8px 0; }
.demo-card p { min-height: 38px; color: #777; }
.demo-card small { display: block; margin-top: 8px; color: #999; }
</style>
