<template>
  <section class="task-board">
    <header class="board-header">
      <div>
        <h2>任务协同看板</h2>
        <p>F2 航站楼空间态势 · 规划/风险/调度全链路实况与历史回溯</p>
      </div>
      <a-space wrap>
        <a-radio-group v-model:value="mode" button-style="solid" size="small">
          <a-radio-button value="live">实况监控</a-radio-button>
          <a-radio-button value="playback">历史回溯</a-radio-button>
        </a-radio-group>
        <a-select
          v-model:value="selectedTaskId"
          style="width: 320px"
          show-search
          :filter-option="filterTaskOption"
          placeholder="选择要查看的任务"
          @change="handleSelectTask"
        >
          <a-select-option v-for="t in taskList" :key="t.id" :value="t.id">
            #{{ t.id }} · {{ t.taskCode }} · {{ statusLabel(t.status) }}
          </a-select-option>
        </a-select>
        <a-button v-if="isOperator" type="primary" @click="quickModalOpen = true">发起位置感知任务</a-button>
        <a-button :loading="loading" @click="refreshAll">刷新</a-button>
      </a-space>
    </header>

    <a-row :gutter="16">
      <!-- 左侧：F2 互动平面图 + POI + 实时路线引导 -->
      <a-col :xs="24" :lg="14">
        <a-card class="map-card" :body-style="{ padding: '12px' }">
          <div class="map-toolbar">
            <a-space wrap size="small">
              <a-button size="small" @click="zoomBy(1.25)">＋</a-button>
              <a-button size="small" @click="zoomBy(0.8)">－</a-button>
              <a-button size="small" @click="focusActiveArea">聚焦活动区</a-button>
              <a-button size="small" @click="fitAll">全图</a-button>
              <a-tag color="blue">{{ Math.round(zoom * 100) }}%</a-tag>
              <a-button
                size="small"
                :type="pickPassengerMode ? 'primary' : 'default'"
                @click="pickPassengerMode = !pickPassengerMode"
              >
                {{ pickPassengerMode ? '点击地图定位旅客中…(点击取消)' : '地图点选旅客位置' }}
              </a-button>
            </a-space>
            <a-space wrap size="small" style="margin-top: 6px;">
              <span style="font-size: 12px; color: #666;">图层：</span>
              <a-checkbox v-model:checked="showPois">航站楼 POI（{{ TERMINAL_POIS.length }}）</a-checkbox>
              <a-checkbox v-model:checked="showRoute">路线引导图</a-checkbox>
              <a-checkbox v-model:checked="showCollabLinks">设备协同连线</a-checkbox>
              <span v-if="routeInfo.totalPixels > 0" class="route-badge">
                引导路径约 {{ routeInfo.totalPixels }} px（{{ routeStopNames.join(' → ') }}）
              </span>
            </a-space>
          </div>

          <div
            ref="viewportRef"
            class="map-viewport"
            :class="{ picking: pickPassengerMode }"
            @wheel.prevent="handleWheel"
            @pointerdown="startPan"
            @pointermove="movePan"
            @pointerup="endPan"
            @pointercancel="endPan"
          >
            <div class="map-canvas" :style="canvasStyle" @click="handleMapClick">
              <img class="floorplan" src="/F2.jpg" alt="F2 平面图" draggable="false" />

              <!-- SVG 路径引导与设备协同连线层 -->
              <svg class="map-svg" :viewBox="`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`">
                <!-- 设备协同连线 -->
                <g v-if="showCollabLinks && collabEdges.length">
                  <line
                    v-for="(edge, idx) in collabEdges"
                    :key="`collab-${idx}`"
                    :x1="edge.x1"
                    :y1="edge.y1"
                    :x2="edge.x2"
                    :y2="edge.y2"
                    stroke="#fa8c16"
                    stroke-width="4"
                    stroke-dasharray="10 8"
                    opacity="0.75"
                  />
                </g>

                <!-- 实时走廊路线引导图 -->
                <g v-if="showRoute && routeInfo.points.length >= 2">
                  <polyline
                    :points="routePolylinePoints"
                    fill="none"
                    stroke="#1677ff"
                    stroke-width="8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    opacity="0.25"
                  />
                  <polyline
                    class="route-animated"
                    :points="routePolylinePoints"
                    fill="none"
                    stroke="#1677ff"
                    stroke-width="5"
                    stroke-dasharray="16 10"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                  <g v-for="(pt, idx) in routeStopPoints" :key="`stop-${idx}`">
                    <circle :cx="pt.x" :cy="pt.y" r="14" fill="#1677ff" stroke="#fff" stroke-width="3" />
                    <text :x="pt.x" :y="pt.y + 5" text-anchor="middle" fill="#fff" font-size="13" font-weight="bold">
                      {{ idx + 1 }}
                    </text>
                  </g>
                </g>
              </svg>

              <!-- 预设 POI 点位 -->
              <template v-if="showPois">
                <div
                  v-for="poi in TERMINAL_POIS"
                  :key="poi.code"
                  class="poi-marker"
                  :style="{ left: `${poi.x}px`, top: `${poi.y}px`, '--poi-color': poiColor(poi.category) }"
                  :title="`${poi.name} (${poi.x}, ${poi.y})`"
                  @click.stop="handlePoiClick(poi)"
                >
                  <span class="poi-dot">{{ poiBadge(poi.category) }}</span>
                  <span class="poi-label">{{ poi.code }}</span>
                </div>
              </template>

              <!-- 旅客当前位置 -->
              <div
                v-if="effectivePassengerPoint"
                class="passenger-marker"
                :style="{ left: `${effectivePassengerPoint.x}px`, top: `${effectivePassengerPoint.y}px` }"
              >
                <span class="passenger-pulse"></span>
                <span class="passenger-icon">🧑</span>
                <span class="passenger-label">旅客：{{ effectivePassengerPoint.label }}</span>
              </div>

              <!-- 7 台实时设备 -->
              <div
                v-for="device in positionedDevices"
                :key="device.deviceCode"
                class="device-marker"
                :class="deviceMarkerClass(device)"
                :style="{ left: `${device.location.x}px`, top: `${device.location.y}px` }"
                :title="`${device.deviceName} (${device.deviceCode})`"
              >
                <span class="device-dot"></span>
                <span class="device-label">
                  {{ device.deviceName }}
                  <template v-if="activeDeviceStepMap[device.agentId]">
                    · 步骤{{ activeDeviceStepMap[device.agentId] }}
                  </template>
                </span>
              </div>
            </div>
          </div>
          <div class="map-footer">
            <span>指针坐标：{{ cursorPos ? `X ${cursorPos.x}, Y ${cursorPos.y}` : '—' }}</span>
            <span>点击 POI 可直接设为旅客起点；支持滚轮缩放、左键拖拽平移</span>
          </div>
        </a-card>
      </a-col>

      <!-- 右侧：全链路决策流水线 + 回放控制 + 设备实时气泡视窗 -->
      <a-col :xs="24" :lg="10">
        <!-- 回放与实时状态栏 -->
        <a-card size="small" style="margin-bottom: 12px">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
              <strong>{{ currentTask?.taskCode || '未选择任务' }}</strong>
              <a-tag v-if="currentTask" :color="statusColor(currentTask.status)" style="margin-left: 8px">
                {{ statusLabel(currentTask.status) }}
              </a-tag>
              <a-tag v-if="mode === 'live' && isRunning(currentTask?.status)" color="processing">2s 实时刷新中</a-tag>
            </div>
            <a-space size="small">
              <a-button size="small" type="primary" @click="togglePlayback">
                {{ playbackPlaying ? '⏸ 暂停回放' : '▶ 过程回放' }}
              </a-button>
              <a-button size="small" @click="resetPlayback">重置</a-button>
              <a-select v-model:value="playbackSpeed" size="small" style="width: 72px">
                <a-select-option :value="1">1x</a-select-option>
                <a-select-option :value="2">2x</a-select-option>
              </a-select>
            </a-space>
          </div>
          <div v-if="currentTask" style="margin-top: 8px; font-size: 12px; color: #555;">
            {{ currentTask.taskGoal }}
          </div>
          <a-progress
            style="margin-top: 8px"
            :percent="stagePercent"
            :status="currentTask?.status === 'FAILED' ? 'exception' : stagePercent === 100 ? 'success' : 'active'"
            size="small"
          />
        </a-card>

        <!-- 全链路决策流水线（5 阶段） -->
        <a-card title="全链路规划与调度实况" size="small" style="margin-bottom: 12px">
          <a-steps direction="vertical" size="small" :current="visibleStageIndex">
            <a-step title="1. 目标理解与空间定位" :status="stageStatus(0)">
              <template #description>
                <div class="stage-desc">
                  <span>场景族：<b>{{ currentTask?.taskFamily || '—' }}</b></span>
                  <span v-if="effectivePassengerPoint"> · 起点：{{ effectivePassengerPoint.label }}</span>
                  <span v-if="effectiveViaPoint"> · 途经：{{ effectiveViaPoint.label }}</span>
                  <span v-if="effectiveDestPoint"> · 目标：{{ effectiveDestPoint.label }}</span>
                </div>
              </template>
            </a-step>
            <a-step title="2. 规划上下文设备快照" :status="stageStatus(1)">
              <template #description>
                <div class="stage-desc">
                  在线设备快照：<b>{{ snapshotSummary }}</b>
                </div>
              </template>
            </a-step>
            <a-step title="3. 模型候选规划与三类校验" :status="stageStatus(2)">
              <template #description>
                <div class="stage-desc">
                  <template v-if="latestModelPlan">
                    模型方案 V{{ latestModelPlan.versionNo }}（{{ latestModelPlan.planSteps?.length || 0 }} 步）·
                    校验：<a-tag :color="latestModelPlan.validationStatus === 'PASSED' ? 'green' : 'red'">
                      {{ latestModelPlan.validationStatus }}
                    </a-tag>
                  </template>
                  <template v-else>尚未生成模型候选计划</template>
                </div>
              </template>
            </a-step>
            <a-step title="4. 监督风险判定与基线降级" :status="stageStatus(3)">
              <template #description>
                <div class="stage-desc">
                  <template v-if="activePlan">
                    当前生效：V{{ activePlan.versionNo }}（{{ activePlan.planSource === 'BASELINE_TEMPLATE' ? '基线模板降级' : '自主规划' }}）·
                    风险：<a-tag :color="activePlan.riskLevel === 'HIGH' ? 'red' : 'green'">{{ activePlan.riskLevel || 'LOW' }}</a-tag>
                    <div v-if="currentTask?.downgradeReason" style="color: #cf1322; margin-top: 2px;">
                      原因：{{ currentTask.downgradeReason }}
                    </div>
                  </template>
                  <template v-else>等待监督判定</template>
                </div>
              </template>
            </a-step>
            <a-step title="5. 动态设备选型与协同执行" :status="stageStatus(4)">
              <template #description>
                <div class="stage-desc">
                  <div v-for="s in visibleSteps" :key="s.stepSeq" class="step-pill">
                    <span>步骤 {{ s.stepSeq }}：{{ capabilityLabel(s.capabilityType) }}</span>
                    <a-tag :color="stepTagColor(s.stepStatus)">{{ s.stepStatus }}</a-tag>
                    <span style="color: #666;">{{ s.deviceName || s.deviceAgentCode || '待分配' }}</span>
                  </div>
                  <div v-if="!visibleSteps.length" style="color: #999;">尚未进入设备分派</div>
                </div>
              </template>
            </a-step>
          </a-steps>
        </a-card>

        <!-- 设备实时视窗（图标 + 对话框气泡） -->
        <a-card title="设备实时展示与执行气泡" size="small">
          <div v-if="!deviceBubbles.length" style="color: #999; font-size: 12px;">
            当前阶段暂无设备指令输出，提交任务或点击“过程回放”查看。
          </div>
          <div class="bubble-list">
            <div v-for="b in deviceBubbles" :key="`${b.stepSeq}-${b.agentCode}`" class="bubble-item">
              <div class="bubble-avatar">{{ b.icon }}</div>
              <div class="bubble-content">
                <div class="bubble-header">
                  <strong>{{ b.deviceLabel }}</strong>
                  <a-tag :color="stepTagColor(b.status)" size="small">{{ b.status }}</a-tag>
                </div>
                <div class="bubble-text">
                  <div v-if="b.commandText"><b>指令：</b>{{ b.commandText }}</div>
                  <div v-if="b.feedbackText" style="color: #389e0d; margin-top: 2px;"><b>回执：</b>{{ b.feedbackText }}</div>
                </div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 发起位置感知任务弹窗 -->
    <a-modal
      v-model:open="quickModalOpen"
      title="发起空间协同演示任务"
      :confirm-loading="quickSubmitting"
      @ok="handleQuickSubmit"
    >
      <a-form layout="vertical">
        <a-form-item label="任务场景">
          <a-select v-model:value="quickForm.scenario">
            <a-select-option value="SPECIAL_PASSENGER_SERVICE">特殊旅客会合与陪同（支持过安检/至登机口）</a-select-option>
            <a-select-option value="FLIGHT_CHANGE_RESPONSE">航班变更发布与多渠道引导</a-select-option>
            <a-select-option value="OVERSIZE_BAGGAGE_HANDLING">行李测量与超规专柜引导</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="旅客 / 事发当前位置（也可在地图点选）">
          <a-select v-model:value="quickForm.origin" show-search>
            <a-select-option v-for="p in TERMINAL_POIS" :key="p.code" :value="p.code">
              {{ p.name }} ({{ p.x }}, {{ p.y }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="quickForm.scenario === 'SPECIAL_PASSENGER_SERVICE'" label="途经安检通道（用于路线引导图，可选）">
          <a-select v-model:value="quickForm.viaSecurity" allow-clear placeholder="不选则直达目的地">
            <a-select-option v-for="p in securityPois" :key="p.code" :value="p.code">{{ p.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标登机口 / 专柜">
          <a-select v-model:value="quickForm.destination" show-search>
            <a-select-option v-for="p in destPois" :key="p.code" :value="p.code">
              {{ p.name }} ({{ p.x }}, {{ p.y }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="quickForm.scenario === 'SPECIAL_PASSENGER_SERVICE'" label="协助类型">
          <a-select v-model:value="quickForm.assistanceType">
            <a-select-option value="轮椅陪同">轮椅陪同</a-select-option>
            <a-select-option value="视障引导">视障引导</a-select-option>
            <a-select-option value="无陪儿童">无陪儿童</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../../store/auth'
import request from '../../api/request'
import {
  getContextSnapshots,
  getPlanVersions,
  getStepAssignments,
  getTask,
  getTaskBoardCommands,
  getTaskEvents,
  listTasks,
  submitTask
} from '../../api/task'
import {
  MAP_HEIGHT,
  MAP_WIDTH,
  POI_CATEGORIES,
  TERMINAL_POIS,
  computeTerminalRoute,
  nearestPoi,
  resolveLocation
} from '../../utils/terminalMap'

const route = useRoute()
const authStore = useAuthStore()
const isOperator = computed(() => authStore.role === 'OPERATOR')

const mode = ref('live')
const loading = ref(false)
const taskList = ref([])
const selectedTaskId = ref(null)
const currentTask = ref(null)
const planVersions = ref([])
const contextSnapshots = ref([])
const stepAssignments = ref([])
const taskEvents = ref([])
const taskCommands = ref([])
const devices = ref([])

// 地图交互状态
const viewportRef = ref(null)
const zoom = ref(0.65)
const pan = reactive({ x: 0, y: -1750 })
const dragging = ref(false)
const dragOrigin = reactive({ x: 0, y: 0, panX: 0, panY: 0 })
const cursorPos = ref(null)
const pickPassengerMode = ref(false)
const manualPassengerPoint = ref(null)

const showPois = ref(true)
const showRoute = ref(true)
const showCollabLinks = ref(true)

// 回放状态
const playbackPlaying = ref(false)
const playbackSpeed = ref(1)
const playbackStep = ref(5) // 0..5 (5 = 全部展示)
let liveTimer = null
let playbackTimer = null

// 快捷发起弹窗
const quickModalOpen = ref(false)
const quickSubmitting = ref(false)
const quickForm = reactive({
  scenario: 'SPECIAL_PASSENGER_SERVICE',
  origin: 'T2值机区',
  viaSecurity: 'VIP安检通道',
  destination: 'GATE_A05',
  assistanceType: '轮椅陪同'
})

const securityPois = TERMINAL_POIS.filter(p => p.category === 'SECURITY')
const destPois = TERMINAL_POIS.filter(p => p.category === 'GATE' || p.category === 'BAGGAGE')

const canvasStyle = computed(() => ({
  width: `${MAP_WIDTH}px`,
  height: `${MAP_HEIGHT}px`,
  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom.value})`,
  transformOrigin: '0 0'
}))

const positionedDevices = computed(() =>
  devices.value.filter(d => d.location && Number.isFinite(Number(d.location.x)) && Number.isFinite(Number(d.location.y)))
)

const sceneParamsObj = computed(() => {
  const raw = currentTask.value?.sceneParams
  if (!raw) return {}
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return {} }
  }
  return raw
})

const effectivePassengerPoint = computed(() => {
  if (manualPassengerPoint.value) return manualPassengerPoint.value
  const sp = sceneParamsObj.value
  const parsed = currentTask.value?.goalParsingResult || {}
  const cand = sp.origin || sp.baggageLocation || parsed.origin
  return resolveLocation(cand, devices.value) || { x: 805, y: 4050, label: 'T2值机区' }
})

const effectiveViaPoint = computed(() => {
  const via = sceneParamsObj.value.viaSecurity || (mode.value === 'live' && quickForm.viaSecurity)
  return via ? resolveLocation(via, devices.value) : null
})

const effectiveDestPoint = computed(() => {
  const sp = sceneParamsObj.value
  const parsed = currentTask.value?.goalParsingResult || {}
  const cand = sp.destination || sp.targetCounter || sp.newGate || parsed.destination
  return resolveLocation(cand, devices.value) || { x: 815, y: 4600, label: 'GATE_A05' }
})

const routeInfo = computed(() => {
  const stops = [effectivePassengerPoint.value, effectiveViaPoint.value, effectiveDestPoint.value].filter(Boolean)
  return computeTerminalRoute(stops)
})

const routePolylinePoints = computed(() =>
  routeInfo.value.points.map(p => `${p.x},${p.y}`).join(' ')
)

const routeStopPoints = computed(() =>
  [effectivePassengerPoint.value, effectiveViaPoint.value, effectiveDestPoint.value].filter(Boolean)
)

const routeStopNames = computed(() => routeStopPoints.value.map(p => p.label || '点位'))

const visibleStageIndex = computed(() => {
  if (mode.value === 'playback') return playbackStep.value
  if (!currentTask.value) return 0
  if (stepAssignments.value.length) return 4
  if (planVersions.value.length) return 3
  if (contextSnapshots.value.length) return 1
  return 0
})

const stagePercent = computed(() => Math.min(100, Math.round((visibleStageIndex.value / 4) * 100)))

const latestModelPlan = computed(() =>
  [...planVersions.value].reverse().find(p => p.planSource !== 'BASELINE_TEMPLATE') || null
)

const activePlan = computed(() => {
  const id = currentTask.value?.currentPlanVersionId
  return planVersions.value.find(p => p.id === id) || planVersions.value[planVersions.value.length - 1] || null
})

const snapshotSummary = computed(() => {
  const snap = contextSnapshots.value[contextSnapshots.value.length - 1]
  if (!snap) return `当前在线设备 ${devices.value.filter(d => d.onlineStatus === 'ONLINE').length} 台`
  return `快照 #${snap.id}（已采集中枢状态）`
})

const mergedSteps = computed(() => {
  const planSteps = activePlan.value?.planSteps || []
  const cmdMap = new Map()
  for (const c of taskCommands.value) {
    cmdMap.set(c.stepSeq, c)
  }
  const devMap = new Map()
  for (const d of devices.value) {
    if (d.agentId) devMap.set(d.agentId, d)
  }
  return stepAssignments.value.map(s => {
    const pStep = planSteps.find(ps => ps.stepSeq === s.stepSeq) || {}
    const cmd = cmdMap.get(s.stepSeq) || {}
    const dev = devMap.get(s.deviceAgentCode) || {}
    return {
      ...s,
      capabilityType: cmd.capabilityType || pStep.capabilityType || s.outputParams?.capabilityType,
      deviceName: dev.deviceName,
      deviceType: dev.simulatedDeviceType || dev.deviceTypeCode,
      inputParams: cmd.inputParams || pStep.inputParams || {}
    }
  })
})

const visibleSteps = computed(() => {
  if (mode.value === 'live') return mergedSteps.value
  if (playbackStep.value < 4) return []
  return mergedSteps.value
})

const activeDeviceStepMap = computed(() => {
  const map = {}
  for (const s of visibleSteps.value) {
    if (s.deviceAgentCode && (s.stepStatus === 'DISPATCHED' || s.stepStatus === 'EXECUTING')) {
      map[s.deviceAgentCode] = s.stepSeq
    }
  }
  return map
})

const collabEdges = computed(() => {
  const dest = effectiveDestPoint.value
  if (!dest) return []
  const edges = []
  for (const s of visibleSteps.value) {
    const dev = devices.value.find(d => d.agentId === s.deviceAgentCode)
    if (dev && dev.location && Number.isFinite(Number(dev.location.x))) {
      edges.push({ x1: Number(dev.location.x), y1: Number(dev.location.y), x2: dest.x, y2: dest.y })
    }
  }
  return edges
})

const deviceBubbles = computed(() => {
  const iconMap = {
    FLIGHT_DELAY_BOARD: '🛫',
    SMART_DISPLAY: '📺',
    BAGGAGE_SCANNER: '🧳',
    MOBILE_ROBOT: '🤖'
  }
  return visibleSteps.value.map(s => {
    const dtype = s.deviceType || inferTypeByCap(s.capabilityType)
    return {
      stepSeq: s.stepSeq,
      agentCode: s.deviceAgentCode || 'UNASSIGNED',
      icon: iconMap[dtype] || '📡',
      deviceLabel: s.deviceName || s.deviceAgentCode || '未分配设备',
      status: s.stepStatus,
      commandText: formatInputSummary(s.capabilityType, s.inputParams),
      feedbackText: formatOutputSummary(s.outputParams, s.reasonCode)
    }
  })
})

function inferTypeByCap(cap) {
  if (cap === 'CAP_FLIGHT_UPDATE') return 'FLIGHT_DELAY_BOARD'
  if (cap === 'CAP_INFO_DISPLAY') return 'SMART_DISPLAY'
  if (cap === 'CAP_BAGGAGE_MEASURE' || cap === 'CAP_OVERSIZE_ALERT') return 'BAGGAGE_SCANNER'
  return 'MOBILE_ROBOT'
}

function formatInputSummary(cap, params) {
  if (!params || !Object.keys(params).length) return capabilityLabel(cap)
  if (cap === 'CAP_FLIGHT_UPDATE') {
    return `${params.flightNumber || ''} [${params.updateType || ''}] ${params.updateContent || ''}`.trim()
  }
  if (cap === 'CAP_INFO_DISPLAY') {
    return params.displayContent || params.message || JSON.stringify(params)
  }
  if (cap === 'CAP_NOTIFICATION') {
    return params.notifyContent || params.message || JSON.stringify(params)
  }
  if (cap === 'CAP_NAVIGATION' || cap === 'CAP_ESCORT') {
    return `前往 ${params.targetLocation || '目标地点'}`
  }
  if (cap === 'CAP_BAGGAGE_MEASURE') {
    return `测量位置：${params.baggageLocation || '默认区域'}`
  }
  return JSON.stringify(params)
}

function formatOutputSummary(out, reasonCode) {
  if (!out || !Object.keys(out).length) return reasonCode || ''
  if (out.arrivalLocation) return `已抵达 ${out.arrivalLocation} (${out.arrivalStatus || 'ARRIVED'})`
  if (out.lengthCm || out.weightKg) {
    return `实测 ${out.lengthCm}×${out.widthCm}×${out.heightCm}cm, ${out.weightKg}kg (${out.isOversize ? '超规' : '正常'})`
  }
  if (out.channelResult === 'UNCOVERED') return `未覆盖：${out.reason || reasonCode}`
  if (out.publishStatus) return `发布 ${out.publishStatus}`
  if (out.displayStatus) return `展示 ${out.displayStatus}`
  if (out.notificationStatus) return `通知 ${out.notificationStatus}`
  return reasonCode || ''
}

function poiColor(cat) {
  return POI_CATEGORIES.find(c => c.key === cat)?.color || '#1677ff'
}

function poiBadge(cat) {
  return POI_CATEGORIES.find(c => c.key === cat)?.badge || 'P'
}

function capabilityLabel(cap) {
  const map = {
    CAP_FLIGHT_UPDATE: '航延屏发布',
    CAP_INFO_DISPLAY: '智慧航显展示',
    CAP_NOTIFICATION: '现场语音/人员通知',
    CAP_NAVIGATION: '机器人导航',
    CAP_ESCORT: '机器人陪同',
    CAP_BAGGAGE_MEASURE: '行李测量',
    CAP_OVERSIZE_ALERT: '超规告警上报'
  }
  return map[cap] || cap || '未知能力'
}

function statusLabel(s) {
  const map = {
    SUBMITTED: '已提交', PLANNING: '待规划', VALIDATING: '校验中',
    EXECUTING: '执行中', COMPLETED: '已完成', FAILED: '失败',
    PENDING_MANUAL: '待人工', MANUAL_TERMINATED: '已终止'
  }
  return map[s] || s || '—'
}

function statusColor(s) {
  if (s === 'COMPLETED') return 'green'
  if (s === 'FAILED' || s === 'PENDING_MANUAL') return 'red'
  if (s === 'EXECUTING' || s === 'PLANNING') return 'blue'
  return 'default'
}

function stepTagColor(s) {
  if (s === 'COMPLETED') return 'green'
  if (s === 'SKIPPED' || s === 'FAILED') return 'red'
  if (s === 'DISPATCHED' || s === 'EXECUTING') return 'blue'
  return 'default'
}

function isRunning(s) {
  return ['SUBMITTED', 'PLANNING', 'VALIDATING', 'EXECUTING', 'REPLANNING', 'PENDING_DISPATCH'].includes(s)
}

function stageStatus(idx) {
  if (visibleStageIndex.value > idx) return 'finish'
  if (visibleStageIndex.value === idx) return 'process'
  return 'wait'
}

function deviceMarkerClass(d) {
  if (d.onlineStatus !== 'ONLINE') return 'offline'
  if (d.workStatus === 'BUSY' || activeDeviceStepMap.value[d.agentId]) return 'busy'
  return 'online'
}

function filterTaskOption(input, option) {
  const text = String(option?.children?.[0]?.children || '')
  return text.toLowerCase().includes(input.toLowerCase())
}

function zoomBy(factor) {
  zoom.value = Math.min(2.0, Math.max(0.2, +(zoom.value * factor).toFixed(2)))
}

function fitAll() {
  zoom.value = 0.25
  pan.x = 180
  pan.y = 20
}

function focusActiveArea() {
  zoom.value = 0.65
  pan.x = 0
  pan.y = -1750
}

function handleWheel(e) {
  zoomBy(e.deltaY < 0 ? 1.12 : 0.88)
}

function startPan(e) {
  if (e.button !== 0) return
  dragging.value = true
  dragOrigin.x = e.clientX
  dragOrigin.y = e.clientY
  dragOrigin.panX = pan.x
  dragOrigin.panY = pan.y
}

function movePan(e) {
  if (viewportRef.value) {
    const rect = viewportRef.value.getBoundingClientRect()
    const mx = Math.round((e.clientX - rect.left - pan.x) / zoom.value)
    const my = Math.round((e.clientY - rect.top - pan.y) / zoom.value)
    if (mx >= 0 && mx <= MAP_WIDTH && my >= 0 && my <= MAP_HEIGHT) {
      cursorPos.value = { x: mx, y: my }
    }
  }
  if (!dragging.value) return
  pan.x = dragOrigin.panX + (e.clientX - dragOrigin.x)
  pan.y = dragOrigin.panY + (e.clientY - dragOrigin.y)
}

function endPan() {
  dragging.value = false
}

function handleMapClick(e) {
  if (!pickPassengerMode.value || !viewportRef.value) return
  const rect = viewportRef.value.getBoundingClientRect()
  const mx = Math.round((e.clientX - rect.left - pan.x) / zoom.value)
  const my = Math.round((e.clientY - rect.top - pan.y) / zoom.value)
  const near = nearestPoi(mx, my)
  manualPassengerPoint.value = { x: mx, y: my, label: near ? `${near.code} 附近` : `(${mx}, ${my})` }
  if (near) quickForm.origin = near.code
  pickPassengerMode.value = false
  message.success(`已设置旅客位置：${manualPassengerPoint.value.label}`)
}

function handlePoiClick(poi) {
  if (pickPassengerMode.value) {
    manualPassengerPoint.value = { x: poi.x, y: poi.y, label: poi.name, code: poi.code }
    quickForm.origin = poi.code
    pickPassengerMode.value = false
    message.success(`已设置旅客起点：${poi.name}`)
  } else {
    message.info(`${poi.name} (${poi.x}, ${poi.y})`)
  }
}

async function loadSnapshot() {
  const res = await request.get('/situation/snapshot')
  devices.value = res.data?.devices || []
}

async function loadTaskDetails(taskId) {
  if (!taskId) return
  const [tRes, pRes, cRes, sRes, eRes, cmdRes] = await Promise.all([
    getTask(taskId),
    getPlanVersions(taskId),
    getContextSnapshots(taskId),
    getStepAssignments(taskId),
    getTaskEvents(taskId),
    getTaskBoardCommands(taskId).catch(() => ({ data: [] }))
  ])
  currentTask.value = tRes.data
  planVersions.value = pRes.data || []
  contextSnapshots.value = cRes.data || []
  stepAssignments.value = sRes.data || []
  taskEvents.value = eRes.data || []
  taskCommands.value = cmdRes.data || []
}

async function refreshAll() {
  loading.value = true
  try {
    const [listRes] = await Promise.all([listTasks({ page: 1, size: 30 }), loadSnapshot()])
    taskList.value = listRes.data?.content || []
    if (!selectedTaskId.value) {
      const qId = Number(route.query.taskId)
      selectedTaskId.value = qId || taskList.value[0]?.id || null
    }
    if (selectedTaskId.value) {
      await loadTaskDetails(selectedTaskId.value)
    }
  } finally {
    loading.value = false
  }
}

async function handleSelectTask(id) {
  manualPassengerPoint.value = null
  await loadTaskDetails(id)
  if (mode.value === 'playback') resetPlayback()
}

function resetPlayback() {
  playbackPlaying.value = false
  clearInterval(playbackTimer)
  playbackStep.value = 0
}

function togglePlayback() {
  if (mode.value !== 'playback') mode.value = 'playback'
  if (playbackPlaying.value) {
    playbackPlaying.value = false
    clearInterval(playbackTimer)
    return
  }
  if (playbackStep.value >= 4) playbackStep.value = 0
  playbackPlaying.value = true
  const intervalMs = Math.round(1500 / playbackSpeed.value)
  playbackTimer = setInterval(() => {
    if (playbackStep.value < 4) {
      playbackStep.value += 1
    } else {
      playbackPlaying.value = false
      clearInterval(playbackTimer)
    }
  }, intervalMs)
}

async function handleQuickSubmit() {
  quickSubmitting.value = true
  try {
    let payload
    if (quickForm.scenario === 'SPECIAL_PASSENGER_SERVICE') {
      const viaText = quickForm.viaSecurity ? `经${quickForm.viaSecurity}` : ''
      payload = {
        taskFamily: 'SPECIAL_PASSENGER_SERVICE',
        taskGoal: `请为虚构${quickForm.assistanceType}旅客在${quickForm.origin}通过智慧航显显示会合提示、通知现场人员，并安排服务机器人前往会合后${viaText}陪同旅客前往${quickForm.destination}。`,
        sceneParams: {
          assistanceType: quickForm.assistanceType,
          origin: quickForm.origin,
          viaSecurity: quickForm.viaSecurity || null,
          destination: quickForm.destination
        }
      }
    } else if (quickForm.scenario === 'FLIGHT_CHANGE_RESPONSE') {
      const today = new Date().toISOString().slice(0, 10)
      payload = {
        taskFamily: 'FLIGHT_CHANGE_RESPONSE',
        taskGoal: `虚构航班CA1234原计划22:30，延误30分钟至23:00，请通过航延屏发布变更、智慧航显发布提示，并由机器人引导旅客从${quickForm.origin}前往${quickForm.destination}。`,
        sceneParams: {
          eventSource: 'MANUAL_FORM',
          flightNumber: 'CA1234',
          changeType: 'DELAY',
          originalTime: `${today}T22:30:00`,
          newTime: `${today}T23:00:00`,
          origin: quickForm.origin,
          newGate: quickForm.destination,
          changeDescription: `虚构航班CA1234延误30分钟，登机口${quickForm.destination}`
        }
      }
    } else {
      payload = {
        taskFamily: 'OVERSIZE_BAGGAGE_HANDLING',
        taskGoal: `请测量${quickForm.origin}当前行李的长宽高和重量；超规时上报告警、由智慧航显发布${quickForm.destination}办理提示，并由移动机器人提供导航；正常行李留存测量结果后结束。`,
        sceneParams: {
          baggageLocation: quickForm.origin,
          targetCounter: quickForm.destination
        }
      }
    }
    const res = await submitTask(payload)
    quickModalOpen.value = false
    mode.value = 'live'
    manualPassengerPoint.value = null
    selectedTaskId.value = res.data.id
    await refreshAll()
    message.success(`已提交协同任务：${res.data.taskCode}`)
  } catch (err) {
    message.error(err?.response?.data?.message || '提交任务失败')
  } finally {
    quickSubmitting.value = false
  }
}

watch(mode, (val) => {
  if (val === 'live') {
    playbackPlaying.value = false
    clearInterval(playbackTimer)
    playbackStep.value = 5
  } else {
    resetPlayback()
  }
})

onMounted(async () => {
  await refreshAll()
  liveTimer = setInterval(async () => {
    if (mode.value === 'live' && selectedTaskId.value) {
      await Promise.all([loadSnapshot(), loadTaskDetails(selectedTaskId.value)]).catch(() => {})
    }
  }, 2000)
})

onBeforeUnmount(() => {
  clearInterval(liveTimer)
  clearInterval(playbackTimer)
})
</script>

<style scoped>
.board-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.board-header h2 { margin: 0; }
.board-header p { margin: 2px 0 0; color: #666; font-size: 13px; }
.map-toolbar { margin-bottom: 8px; }
.route-badge {
  background: #e6f4ff;
  color: #0958d9;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.map-viewport {
  position: relative;
  height: 620px;
  overflow: hidden;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #f5f5f5;
  cursor: grab;
  user-select: none;
}
.map-viewport.picking { cursor: crosshair; }
.map-canvas { position: relative; }
.floorplan { width: 1260px; height: 6895px; display: block; pointer-events: none; }
.map-svg { position: absolute; left: 0; top: 0; width: 1260px; height: 6895px; pointer-events: none; }
.route-animated { animation: dashMove 1.2s linear infinite; }
@keyframes dashMove {
  to { stroke-dashoffset: -52; }
}
.poi-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  z-index: 4;
}
.poi-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--poi-color);
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.25);
}
.poi-label {
  background: rgba(255,255,255,0.92);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #262626;
  border: 1px solid #d9d9d9;
  white-space: nowrap;
}
.passenger-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 12;
  pointer-events: none;
}
.passenger-pulse {
  position: absolute;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(22, 119, 255, 0.25);
  animation: pulse 1.5s infinite;
}
.passenger-icon { font-size: 24px; position: relative; }
.passenger-label {
  background: #1677ff;
  color: #fff;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
}
.device-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 4px;
  z-index: 8;
}
.device-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0,0,0,0.35);
}
.device-marker.online .device-dot { background: #52c41a; }
.device-marker.busy .device-dot { background: #fa8c16; animation: pulse 1.2s infinite; }
.device-marker.offline .device-dot { background: #8c8c8c; }
.device-label {
  background: rgba(0,0,0,0.75);
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
}
@keyframes pulse {
  0% { transform: scale(1); opacity: 0.9; }
  70% { transform: scale(1.6); opacity: 0.2; }
  100% { transform: scale(1); opacity: 0.9; }
}
.map-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #888;
  margin-top: 6px;
}
.stage-desc { font-size: 12px; color: #444; }
.step-pill { display: flex; align-items: center; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
.bubble-list { display: flex; flex-direction: column; gap: 10px; max-height: 260px; overflow-y: auto; }
.bubble-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 8px 10px;
}
.bubble-avatar {
  font-size: 24px;
  line-height: 1;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 50%;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.bubble-content { flex: 1; font-size: 12px; }
.bubble-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.bubble-text { color: #333; word-break: break-word; }
</style>
