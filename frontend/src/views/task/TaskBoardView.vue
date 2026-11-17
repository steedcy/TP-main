<template>
  <section class="task-board">
    <header class="board-header">
      <div>
        <h2>任务协同看板（Leaflet-Geoman 室内矢量地图）</h2>
        <p>F2 航站楼空间态势 · 规划/风险/调度全链路实况、历史回溯与矢量地图编辑</p>
      </div>
      <a-space wrap>
        <a-radio-group v-model:value="mode" button-style="solid" size="small">
          <a-radio-button value="live">实况监控</a-radio-button>
          <a-radio-button value="playback">历史回溯</a-radio-button>
        </a-radio-group>
        <a-select
          v-model:value="selectedTaskId"
          style="width: 300px"
          show-search
          :filter-option="filterTaskOption"
          placeholder="选择要查看的任务"
          @change="handleSelectTask"
        >
          <a-select-option v-for="t in taskList" :key="t.id" :value="t.id">
            #{{ t.id }} · {{ t.taskCode }} · {{ statusLabel(t.status) }}
          </a-select-option>
        </a-select>
        <a-button v-if="isOperator" @click="spaceDrawerOpen = true">空间 POI 与区域管理</a-button>
        <a-button v-if="isOperator" type="primary" @click="quickModalOpen = true">发起位置感知任务</a-button>
        <a-button :loading="loading" @click="refreshAll">刷新</a-button>
      </a-space>
    </header>

    <a-alert
      v-if="pickPassengerMode"
      type="info"
      show-icon
      style="margin-bottom: 12px"
      message="请在地图上直接点击旅客当前所在位置（或点击任意 POI 点位）"
    >
      <template #action>
        <a-button size="small" @click="pickPassengerMode = false">取消</a-button>
      </template>
    </a-alert>

    <a-row :gutter="16">
      <!-- 左侧：Leaflet + Leaflet-Geoman 室内矢量地图 -->
      <a-col :xs="24" :lg="14">
        <a-card class="map-card" :body-style="{ padding: '12px' }">
          <div class="map-toolbar">
            <a-space wrap size="small">
              <a-button size="small" @click="mapEditorRef?.focusActiveArea()">聚焦活动区</a-button>
              <a-button size="small" @click="mapEditorRef?.fitAll()">查看全图</a-button>
              <a-button
                size="small"
                :type="pickPassengerMode ? 'primary' : 'default'"
                @click="pickPassengerMode = !pickPassengerMode"
              >
                {{ pickPassengerMode ? '点选旅客位置中…' : '地图点选旅客位置' }}
              </a-button>
              <a-button size="small" @click="handleExportGeoJson">导出 GeoJSON</a-button>
              <label v-if="isOperator" class="geojson-import-btn">
                <a-button size="small">导入 GeoJSON</a-button>
                <input type="file" accept=".json,.geojson" style="display: none" @change="handleImportGeoJson" />
              </label>
            </a-space>
            <a-space wrap size="small" style="margin-top: 6px;">
              <span style="font-size: 12px; color: #666;">图层：</span>
              <a-checkbox v-model:checked="showPois">POI 点位（{{ pois.length }}）</a-checkbox>
              <a-checkbox v-model:checked="showRegions">功能区域/走廊（{{ regions.length }}）</a-checkbox>
              <a-checkbox v-model:checked="showRoute">路线引导图</a-checkbox>
              <a-checkbox v-model:checked="showCollabLinks">设备协同连线</a-checkbox>
              <span v-if="routeInfo.totalPixels > 0" class="route-badge">
                引导路径约 {{ routeInfo.totalPixels }} 像素（{{ routeStopNames.join(' → ') }}）
              </span>
            </a-space>
          </div>

          <IndoorMapEditor
            ref="mapEditorRef"
            :editable="isOperator"
            :pois="pois"
            :regions="regions"
            :devices="devices"
            :passenger-point="effectivePassengerPoint"
            :route-points="routeInfo.points"
            :stop-points="routeStopPoints"
            :collab-edges="collabEdges"
            :active-device-step-map="activeDeviceStepMap"
            :show-pois="showPois"
            :show-regions="showRegions"
            :show-route="showRoute"
            :show-collab-links="showCollabLinks"
            :pick-passenger-mode="pickPassengerMode"
            @cursor-move="cursorPos = $event"
            @pick-passenger="handlePickPassenger"
            @poi-click="handlePoiClick"
            @create-poi="handleGeomanCreatePoi"
            @update-poi="handleGeomanUpdatePoi"
            @delete-poi="handleDeletePoi"
            @create-region="handleGeomanCreateRegion"
            @update-region="handleGeomanUpdateRegion"
            @delete-region="handleDeleteRegion"
          />

          <div class="map-footer">
            <span>指针坐标：{{ cursorPos ? `X ${cursorPos.x}, Y ${cursorPos.y}` : '—' }}</span>
            <span>左上角工具栏支持 Leaflet-Geoman 矢量标注、顶点吸附、拖拽编辑、擦除删除与 GeoJSON 互通</span>
          </div>
        </a-card>
      </a-col>

      <!-- 右侧：全链路决策流水线 + 回放控制 + 设备实时气泡视窗 -->
      <a-col :xs="24" :lg="10">
        <a-card size="small" style="margin-bottom: 12px">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
              <strong>{{ currentTask?.taskCode || '未选择任务' }}</strong>
              <a-tag v-if="currentTask" :color="statusColor(currentTask.status)" style="margin-left: 8px">
                {{ statusLabel(currentTask.status) }}
              </a-tag>
              <a-tag v-if="mode === 'live' && isRunning(currentTask?.status)" color="processing">每 2 秒自动刷新</a-tag>
            </div>
            <a-space size="small">
              <a-button size="small" type="primary" @click="togglePlayback">
                {{ playbackPlaying ? '⏸ 暂停回放' : '▶ 过程回放' }}
              </a-button>
              <a-button size="small" @click="resetPlayback">重置</a-button>
              <a-select v-model:value="playbackSpeed" size="small" style="width: 72px">
                <a-select-option :value="1">1倍速</a-select-option>
                <a-select-option :value="2">2倍速</a-select-option>
              </a-select>
            </a-space>
          </div>
          <div v-if="currentTask" style="margin-top: 8px; font-size: 12px; color: #555;">
            <b>任务目标：</b>{{ currentTask.taskGoal }}
          </div>
          <a-progress
            style="margin-top: 8px"
            :percent="stagePercent"
            :status="currentTask?.status === 'FAILED' ? 'exception' : stagePercent === 100 ? 'success' : 'active'"
            size="small"
          />
        </a-card>

        <a-card title="全链路规划与调度实况" size="small" style="margin-bottom: 12px">
          <a-steps direction="vertical" size="small" :current="visibleStageIndex">
            <a-step title="1. 目标理解与空间定位" :status="stageStatus(0)">
              <template #description>
                <div class="stage-desc">
                  <span>业务场景：<b>{{ translateTaskFamily(currentTask?.taskFamily) }}</b></span>
                  <span v-if="effectivePassengerPoint"> · 起点：{{ effectivePassengerPoint.label }}</span>
                  <span v-if="effectiveViaPoint"> · 途经：{{ effectiveViaPoint.label }}</span>
                  <span v-if="effectiveDestPoint"> · 目标：{{ effectiveDestPoint.label }}</span>
                </div>
              </template>
            </a-step>
            <a-step title="2. 规划上下文设备快照" :status="stageStatus(1)">
              <template #description>
                <div class="stage-desc">
                  可用资源快照：<b>{{ snapshotSummary }}</b>
                </div>
              </template>
            </a-step>
            <a-step title="3. 模型候选规划与三类校验" :status="stageStatus(2)">
              <template #description>
                <div class="stage-desc">
                  <template v-if="latestModelPlan">
                    模型生成方案第 {{ latestModelPlan.versionNo }} 版（共 {{ latestModelPlan.planSteps?.length || 0 }} 个步骤）·
                    校验结果：<a-tag :color="latestModelPlan.validationStatus === 'PASSED' ? 'green' : 'red'">
                      {{ latestModelPlan.validationStatus === 'PASSED' ? '校验通过' : '校验拦截' }}
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
                    当前生效方案：第 {{ activePlan.versionNo }} 版（{{ activePlan.planSource === 'BASELINE_TEMPLATE' ? '基线模板降级' : '自主规划执行' }}）·
                    风险等级：<a-tag :color="activePlan.riskLevel === 'HIGH' ? 'red' : 'green'">
                      {{ activePlan.riskLevel === 'HIGH' ? '高风险' : '低风险' }}
                    </a-tag>
                    <div v-if="currentTask?.downgradeReason" style="color: #cf1322; margin-top: 2px;">
                      降级说明：{{ currentTask.downgradeReason }}
                    </div>
                  </template>
                  <template v-else>等待监督智能体判定</template>
                </div>
              </template>
            </a-step>
            <a-step title="5. 动态设备选型与协同执行" :status="stageStatus(4)">
              <template #description>
                <div class="stage-desc">
                  <div v-for="s in visibleSteps" :key="s.stepSeq" class="step-pill">
                    <span>第 {{ s.stepSeq }} 步：{{ capabilityLabel(s.capabilityType) }}</span>
                    <a-tag :color="stepTagColor(s.stepStatus)">{{ translateStepStatus(s.stepStatus) }}</a-tag>
                    <span style="color: #666;">执行设备：{{ s.deviceName || '未分配' }}</span>
                  </div>
                  <div v-if="!visibleSteps.length" style="color: #999;">尚未进入设备分派阶段</div>
                </div>
              </template>
            </a-step>
          </a-steps>
        </a-card>

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
                  <a-tag :color="stepTagColor(b.status)" size="small">{{ translateStepStatus(b.status) }}</a-tag>
                </div>
                <div class="bubble-text">
                  <div v-if="b.commandText"><b>下发指令：</b>{{ b.commandText }}</div>
                  <div v-if="b.feedbackText" style="color: #389e0d; margin-top: 2px;"><b>设备回执：</b>{{ b.feedbackText }}</div>
                </div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 空间 POI 与区域管理抽屉（仅运行操作员） -->
    <a-drawer v-model:open="spaceDrawerOpen" title="空间 POI 与功能区域/走廊管理" width="580">
      <a-tabs>
        <a-tab-pane key="pois" tab="POI 点位管理">
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <a-space>
              <a-button type="primary" size="small" @click="openPoiModal(null)">新增 POI</a-button>
              <a-button size="small" :loading="syncingScanners" @click="handleSyncScanners">同步行李测量仿真体坐标</a-button>
            </a-space>
            <a-select v-model:value="poiCategoryFilter" size="small" style="width: 180px" allow-clear placeholder="按类型筛选">
              <a-select-option v-for="c in POI_CATEGORIES" :key="c.key" :value="c.key">{{ c.label }}</a-select-option>
            </a-select>
          </div>
          <a-table :data-source="filteredPois" :pagination="{ pageSize: 8 }" size="small" row-key="poiCode">
            <a-table-column title="名称" data-index="poiName" key="poiName" />
            <a-table-column title="类型" key="category">
              <template #default="{ record }">
                <a-tag :color="poiColor(record.category)">{{ poiCategoryLabel(record.category) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="坐标 (X, Y)" key="coords">
              <template #default="{ record }">{{ Math.round(record.x) }}, {{ Math.round(record.y) }}</template>
            </a-table-column>
            <a-table-column title="操作" key="actions" width="120">
              <template #default="{ record }">
                <a-space size="small">
                  <a-button type="link" size="small" style="padding: 0" @click="openPoiModal(record)">编辑</a-button>
                  <a-popconfirm v-if="record.id" title="确认删除该 POI？" @confirm="handleDeletePoi(record.id)">
                    <a-button type="link" size="small" danger style="padding: 0">删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </a-table-column>
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="regions" tab="功能区域与走廊">
          <p style="font-size: 12px; color: #666; margin-bottom: 12px;">
            请使用地图左上角 Leaflet-Geoman 工具栏直接绘制多边形/折线、拖拽修改顶点或使用橡皮擦删除。
          </p>
          <a-table :data-source="regions" :pagination="false" size="small" row-key="id">
            <a-table-column title="区域名称" data-index="regionName" key="regionName" />
            <a-table-column title="类型" key="regionType">
              <template #default="{ record }">
                <a-tag :color="record.regionType === 'ISOLATED_ZONE' ? 'purple' : record.regionType === 'CHECKIN_HALL' ? 'green' : 'cyan'">
                  {{ record.regionType === 'ISOLATED_ZONE' ? '安检后候机隔离区' : record.regionType === 'CHECKIN_HALL' ? '值机办理区' : '通行走廊' }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作" key="actions" width="80">
              <template #default="{ record }">
                <a-popconfirm title="确认删除该区域？" @confirm="handleDeleteRegion(record.id)">
                  <a-button type="link" size="small" danger style="padding: 0">删除</a-button>
                </a-popconfirm>
              </template>
            </a-table-column>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </a-drawer>

    <!-- 新增/编辑 POI 弹窗 -->
    <a-modal v-model:open="poiModalOpen" :title="poiForm.id ? '编辑 POI 点位' : '新增 POI 点位'" @ok="handleSavePoi">
      <a-form layout="vertical">
        <a-form-item label="POI 编码（唯一标识）">
          <a-input v-model:value="poiForm.poiCode" :disabled="Boolean(poiForm.id)" placeholder="例如 GATE_A08 或 母婴室01" />
        </a-form-item>
        <a-form-item label="POI 中文名称">
          <a-input v-model:value="poiForm.poiName" placeholder="例如 登机口 A08 或 2号母婴室" />
        </a-form-item>
        <a-form-item label="POI 类型">
          <a-select v-model:value="poiForm.category" @change="handlePoiCategoryChange">
            <a-select-option v-for="c in POI_CATEGORIES" :key="c.key" :value="c.key">{{ c.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="poiForm.category === 'MEASURE'" label="关联行李测量仿真体（选择后自动填入其坐标）">
          <a-select v-model:value="poiForm.linkedDeviceCode" allow-clear @change="handleScannerDeviceSelect">
            <a-select-option v-for="d in scannerDevices" :key="d.deviceCode" :value="d.deviceCode">
              {{ d.deviceName }} ({{ d.deviceCode }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="X 坐标（像素）"><a-input-number v-model:value="poiForm.x" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Y 坐标（像素）"><a-input-number v-model:value="poiForm.y" style="width: 100%" /></a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="所属区域（可选）">
          <a-input v-model:value="poiForm.zone" placeholder="如 候机隔离区 / 值机办理区" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 保存 Geoman 绘制区域弹窗 -->
    <a-modal v-model:open="regionModalOpen" title="保存矢量绘制区域" @ok="handleSaveRegion">
      <a-form layout="vertical">
        <a-form-item label="区域类型">
          <a-select v-model:value="regionForm.regionType">
            <a-select-option v-if="regionForm.regionType === 'CORRIDOR'" value="CORRIDOR">通行走廊（贯穿登机口通道）</a-select-option>
            <template v-else>
              <a-select-option value="ISOLATED_ZONE">安检后候机隔离区</a-select-option>
              <a-select-option value="CHECKIN_HALL">值机与行李托运办理区</a-select-option>
            </template>
          </a-select>
        </a-form-item>
        <a-form-item label="区域名称">
          <a-input v-model:value="regionForm.regionName" placeholder="如：T2候机隔离区 / A指廊主走廊" />
        </a-form-item>
      </a-form>
    </a-modal>

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
            <a-select-option value="SPECIAL_PASSENGER_SERVICE">特殊旅客协同服务（支持经安检至登机口/设施）</a-select-option>
            <a-select-option value="FLIGHT_CHANGE_RESPONSE">航班变更发布与多渠道引导</a-select-option>
            <a-select-option value="OVERSIZE_BAGGAGE_HANDLING">行李测量与超规专柜引导</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="旅客 / 事发当前位置（也可先在地图点选）">
          <a-select v-model:value="quickForm.origin" show-search>
            <a-select-option v-for="p in pois" :key="p.poiCode" :value="p.poiCode">
              {{ p.poiName }} ({{ Math.round(p.x) }}, {{ Math.round(p.y) }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="quickForm.scenario === 'SPECIAL_PASSENGER_SERVICE'" label="途经安检通道（用于路线引导图，可选）">
          <a-select v-model:value="quickForm.viaSecurity" allow-clear placeholder="不选则直达目的地">
            <a-select-option v-for="p in securityPois" :key="p.poiCode" :value="p.poiCode">{{ p.poiName }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标登机口 / 专柜 / 商铺或设施">
          <a-select v-model:value="quickForm.destination" show-search>
            <a-select-option v-for="p in destPois" :key="p.poiCode" :value="p.poiCode">
              {{ p.poiName }} ({{ Math.round(p.x) }}, {{ Math.round(p.y) }})
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
import IndoorMapEditor from '../../components/IndoorMapEditor.vue'
import {
  createMapRegion,
  createPoi,
  deleteMapRegion,
  deletePoi,
  getContextSnapshots,
  getMapLayout,
  getPlanVersions,
  getStepAssignments,
  getTask,
  getTaskBoardCommands,
  getTaskEvents,
  listTasks,
  submitTask,
  syncScannerPois,
  updateMapRegion,
  updatePoi
} from '../../api/task'
import {
  DEFAULT_TERMINAL_POIS,
  POI_CATEGORIES,
  computeTerminalRoute,
  formatReadableCommand,
  formatReadableFeedback,
  nearestPoi,
  resolveLocation,
  translateStepStatus,
  translateTaskFamily
} from '../../utils/terminalMap'

const route = useRoute()
const authStore = useAuthStore()
const isOperator = computed(() => authStore.role === 'OPERATOR')

const mapEditorRef = ref(null)
const mode = ref('live')
const loading = ref(false)
const taskList = ref([])
const selectedTaskId = ref(null)
const currentTask = ref(null)
const planVersions = ref([])
const contextSnapshots = ref([])
const stepAssignments = ref([])
const taskCommands = ref([])
const devices = ref([])

const pois = ref([...DEFAULT_TERMINAL_POIS])
const regions = ref([])
const cursorPos = ref(null)
const pickPassengerMode = ref(false)
const manualPassengerPoint = ref(null)

const showPois = ref(true)
const showRegions = ref(true)
const showRoute = ref(true)
const showCollabLinks = ref(true)

const spaceDrawerOpen = ref(false)
const poiCategoryFilter = ref(undefined)
const syncingScanners = ref(false)
const poiModalOpen = ref(false)
const poiForm = reactive({
  id: null,
  poiCode: '',
  poiName: '',
  category: 'GATE',
  x: 600,
  y: 4200,
  zone: '',
  linkedDeviceCode: null
})

const regionModalOpen = ref(false)
const regionForm = reactive({
  regionType: 'ISOLATED_ZONE',
  regionName: '',
  points: []
})

const playbackPlaying = ref(false)
const playbackSpeed = ref(1)
const playbackStep = ref(5)
let liveTimer = null
let playbackTimer = null

const quickModalOpen = ref(false)
const quickSubmitting = ref(false)
const quickForm = reactive({
  scenario: 'SPECIAL_PASSENGER_SERVICE',
  origin: 'T2值机区',
  viaSecurity: 'VIP安检通道',
  destination: 'GATE_A05',
  assistanceType: '轮椅陪同'
})

const filteredPois = computed(() =>
  poiCategoryFilter.value ? pois.value.filter(p => p.category === poiCategoryFilter.value) : pois.value
)
const scannerDevices = computed(() =>
  devices.value.filter(d => (d.simulatedDeviceType || d.deviceTypeCode) === 'BAGGAGE_SCANNER')
)
const securityPois = computed(() => pois.value.filter(p => p.category === 'SECURITY'))
const destPois = computed(() =>
  pois.value.filter(p => ['GATE', 'BAGGAGE', 'SHOP', 'FACILITY', 'SERVICE'].includes(p.category))
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
  return resolveLocation(cand, pois.value, devices.value) || resolveLocation('T2值机区', pois.value, devices.value)
})

const effectiveViaPoint = computed(() => {
  const via = sceneParamsObj.value.viaSecurity || (mode.value === 'live' && quickForm.viaSecurity)
  return via ? resolveLocation(via, pois.value, devices.value) : null
})

const effectiveDestPoint = computed(() => {
  const sp = sceneParamsObj.value
  const parsed = currentTask.value?.goalParsingResult || {}
  const cand = sp.destination || sp.targetCounter || sp.newGate || parsed.destination
  return resolveLocation(cand, pois.value, devices.value) || resolveLocation('GATE_A05', pois.value, devices.value)
})

const routeInfo = computed(() => {
  const stops = [effectivePassengerPoint.value, effectiveViaPoint.value, effectiveDestPoint.value].filter(Boolean)
  return computeTerminalRoute(stops, regions.value)
})

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
  return `上下文快照 #${snap.id}（已采集中枢与设备实时状态）`
})

const mergedSteps = computed(() => {
  const planSteps = activePlan.value?.planSteps || []
  const cmdMap = new Map()
  for (const c of taskCommands.value) cmdMap.set(c.stepSeq, c)
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
  const iconMap = { FLIGHT_DELAY_BOARD: '🛫', SMART_DISPLAY: '📺', BAGGAGE_SCANNER: '🧳', MOBILE_ROBOT: '🤖' }
  return visibleSteps.value.map(s => {
    const dtype = s.deviceType || inferTypeByCap(s.capabilityType)
    return {
      stepSeq: s.stepSeq,
      agentCode: s.deviceAgentCode || 'UNASSIGNED',
      icon: iconMap[dtype] || '📡',
      deviceLabel: s.deviceName || (dtype ? deviceTypeZh(dtype) : '待分派设备'),
      status: s.stepStatus,
      commandText: formatReadableCommand(s.capabilityType, s.inputParams) || capabilityLabel(s.capabilityType),
      feedbackText: formatReadableFeedback(s.outputParams, s.reasonCode)
    }
  })
})

function inferTypeByCap(cap) {
  if (cap === 'CAP_FLIGHT_UPDATE') return 'FLIGHT_DELAY_BOARD'
  if (cap === 'CAP_INFO_DISPLAY') return 'SMART_DISPLAY'
  if (cap === 'CAP_BAGGAGE_MEASURE' || cap === 'CAP_OVERSIZE_ALERT') return 'BAGGAGE_SCANNER'
  return 'MOBILE_ROBOT'
}

function deviceTypeZh(dtype) {
  const map = {
    FLIGHT_DELAY_BOARD: '航班信息屏仿真体',
    SMART_DISPLAY: '智慧显示终端仿真体',
    BAGGAGE_SCANNER: '行李测量仪仿真体',
    MOBILE_ROBOT: '移动服务机器人仿真体'
  }
  return map[dtype] || '智能设备'
}

function poiColor(cat) { return POI_CATEGORIES.find(c => c.key === cat)?.color || '#1677ff' }
function poiCategoryLabel(cat) { return POI_CATEGORIES.find(c => c.key === cat)?.label || cat }

function capabilityLabel(cap) {
  const map = {
    CAP_FLIGHT_UPDATE: '航延屏信息发布',
    CAP_INFO_DISPLAY: '智慧航显引导展示',
    CAP_NOTIFICATION: '现场语音/人员通知',
    CAP_NAVIGATION: '机器人移动引导',
    CAP_ESCORT: '机器人陪同护送',
    CAP_BAGGAGE_MEASURE: '智能行李测量',
    CAP_OVERSIZE_ALERT: '超规行李告警上报'
  }
  return map[cap] || cap || '协同执行步骤'
}

function statusLabel(s) {
  const map = {
    SUBMITTED: '已提交', PLANNING: '待规划', VALIDATING: '校验中',
    EXECUTING: '执行中', COMPLETED: '已完成', FAILED: '已失败',
    PENDING_MANUAL: '待人工处理', MANUAL_TERMINATED: '已人工终止'
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

function filterTaskOption(input, option) {
  const text = String(option?.children?.[0]?.children || '')
  return text.toLowerCase().includes(input.toLowerCase())
}

function handlePickPassenger(pt) {
  if (pt.code) {
    manualPassengerPoint.value = pt
    quickForm.origin = pt.code
  } else {
    const near = nearestPoi(pt.x, pt.y, pois.value)
    manualPassengerPoint.value = { x: pt.x, y: pt.y, label: near ? `${near.poiName}附近` : `(${pt.x}, ${pt.y})` }
    if (near) quickForm.origin = near.poiCode
  }
  pickPassengerMode.value = false
  message.success(`已设置旅客位置：${manualPassengerPoint.value.label}`)
}

function handlePoiClick(poi) {
  message.info(`${poi.poiName}（${poiCategoryLabel(poi.category)}，坐标 ${Math.round(poi.x)}, ${Math.round(poi.y)}）`)
}

function handleGeomanCreatePoi(pt) {
  openPoiModal({ poiCode: `POI_${Date.now()}`, poiName: '', category: 'GATE', x: pt.x, y: pt.y, zone: '' })
}

async function handleGeomanUpdatePoi(poi) {
  try {
    const res = await updatePoi(poi.id, poi)
    pois.value = res.data || []
    message.success(`已更新 POI「${poi.poiName}」坐标 (${poi.x}, ${poi.y})`)
  } catch (err) {
    message.error(err?.response?.data?.message || '更新 POI 失败')
  }
}

function handleGeomanCreateRegion({ regionType, points }) {
  regionForm.regionType = regionType
  regionForm.regionName = regionType === 'CORRIDOR' ? '新建通行走廊' : '安检后候机隔离区'
  regionForm.points = points
  regionModalOpen.value = true
}

async function handleGeomanUpdateRegion({ id, regionName, regionType, points }) {
  try {
    const res = await updateMapRegion(id, {
      regionName,
      regionType,
      geometryJson: JSON.stringify(points)
    })
    regions.value = res.data || []
    message.success(`已更新区域「${regionName}」几何边界`)
  } catch (err) {
    message.error(err?.response?.data?.message || '更新区域失败')
  }
}

async function handleSaveRegion() {
  if (!regionForm.regionName.trim()) {
    message.warning('请输入区域名称')
    return
  }
  const res = await createMapRegion({
    regionCode: `${regionForm.regionType}_${Date.now()}`,
    regionName: regionForm.regionName.trim(),
    regionType: regionForm.regionType,
    geometryJson: JSON.stringify(regionForm.points)
  })
  regions.value = res.data || []
  regionModalOpen.value = false
  message.success('已保存矢量区域')
}

async function handleDeleteRegion(id) {
  const res = await deleteMapRegion(id)
  regions.value = res.data || []
  message.success('已删除区域')
}

function openPoiModal(record) {
  if (record) {
    Object.assign(poiForm, {
      id: record.id || null,
      poiCode: record.poiCode,
      poiName: record.poiName,
      category: record.category,
      x: Number(record.x),
      y: Number(record.y),
      zone: record.zone || '',
      linkedDeviceCode: record.linkedDeviceCode || null
    })
  } else {
    Object.assign(poiForm, { id: null, poiCode: '', poiName: '', category: 'GATE', x: 600, y: 4200, zone: '', linkedDeviceCode: null })
  }
  poiModalOpen.value = true
}

function handlePoiCategoryChange(val) {
  if (val === 'MEASURE' && scannerDevices.value.length && !poiForm.linkedDeviceCode) {
    poiForm.linkedDeviceCode = scannerDevices.value[0].deviceCode
    handleScannerDeviceSelect(poiForm.linkedDeviceCode)
  }
}

function handleScannerDeviceSelect(code) {
  const dev = scannerDevices.value.find(d => d.deviceCode === code)
  if (dev && dev.location && Number.isFinite(Number(dev.location.x))) {
    poiForm.x = Number(dev.location.x)
    poiForm.y = Number(dev.location.y)
    if (!poiForm.poiName) poiForm.poiName = `${dev.deviceName}测量点`
    if (!poiForm.poiCode) poiForm.poiCode = `测量点_${dev.deviceCode}`
  }
}

async function handleSavePoi() {
  try {
    const res = poiForm.id ? await updatePoi(poiForm.id, { ...poiForm }) : await createPoi({ ...poiForm })
    pois.value = res.data || []
    poiModalOpen.value = false
    message.success('POI 点位已保存')
  } catch (err) {
    message.error(err?.response?.data?.message || '保存 POI 失败')
  }
}

async function handleDeletePoi(id) {
  const res = await deletePoi(id)
  pois.value = res.data || []
  message.success('已删除 POI')
}

async function handleSyncScanners() {
  syncingScanners.value = true
  try {
    const res = await syncScannerPois()
    pois.value = res.data || []
    message.success('已自动同步智能行李测量仿真体实时坐标')
  } finally {
    syncingScanners.value = false
  }
}

function handleExportGeoJson() {
  const geo = mapEditorRef.value?.exportGeoJson()
  if (!geo) return
  const blob = new Blob([JSON.stringify(geo, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `f2-terminal-layout-${Date.now()}.geojson`
  a.click()
  URL.revokeObjectURL(url)
  message.success('已导出标准 GeoJSON 矢量文件')
}

async function handleImportGeoJson(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const geo = JSON.parse(await file.text())
    const features = Array.isArray(geo.features) ? geo.features : []
    let count = 0
    for (const f of features) {
      const p = f.properties || {}
      if (f.geometry?.type === 'Point' && Array.isArray(f.geometry.coordinates)) {
        const [x, y] = f.geometry.coordinates
        await createPoi({
          poiCode: p.poiCode || `GEO_POI_${Date.now()}_${count}`,
          poiName: p.poiName || p.name || `导入点位 ${count + 1}`,
          category: p.category || 'SERVICE',
          x,
          y,
          zone: p.zone || ''
        }).catch(() => {})
        count++
      } else if (f.geometry?.type === 'LineString' && Array.isArray(f.geometry.coordinates)) {
        const pts = f.geometry.coordinates.map(([x, y]) => ({ x, y }))
        await createMapRegion({
          regionCode: p.regionCode || `GEO_CORR_${Date.now()}_${count}`,
          regionName: p.regionName || p.name || `导入走廊 ${count + 1}`,
          regionType: 'CORRIDOR',
          geometryJson: JSON.stringify(pts)
        }).catch(() => {})
        count++
      } else if (f.geometry?.type === 'Polygon' && Array.isArray(f.geometry.coordinates?.[0])) {
        const pts = f.geometry.coordinates[0].slice(0, -1).map(([x, y]) => ({ x, y }))
        await createMapRegion({
          regionCode: p.regionCode || `GEO_ZONE_${Date.now()}_${count}`,
          regionName: p.regionName || p.name || `导入区域 ${count + 1}`,
          regionType: p.regionType || 'ISOLATED_ZONE',
          geometryJson: JSON.stringify(pts)
        }).catch(() => {})
        count++
      }
    }
    await loadMapLayoutData()
    message.success(`已导入 ${count} 项 GeoJSON 要素`)
  } catch {
    message.error('GeoJSON 文件解析失败')
  } finally {
    e.target.value = ''
  }
}

async function loadMapLayoutData() {
  try {
    const res = await getMapLayout()
    if (res.data?.pois?.length) pois.value = res.data.pois
    regions.value = res.data?.regions || []
  } catch {}
}

async function loadSnapshot() {
  const res = await request.get('/situation/snapshot')
  devices.value = res.data?.devices || []
}

async function loadTaskDetails(taskId) {
  if (!taskId) return
  const [tRes, pRes, cRes, sRes, cmdRes] = await Promise.all([
    getTask(taskId),
    getPlanVersions(taskId),
    getContextSnapshots(taskId),
    getStepAssignments(taskId),
    getTaskBoardCommands(taskId).catch(() => ({ data: [] }))
  ])
  currentTask.value = tRes.data
  planVersions.value = pRes.data || []
  contextSnapshots.value = cRes.data || []
  stepAssignments.value = sRes.data || []
  taskCommands.value = cmdRes.data || []
}

async function refreshAll() {
  loading.value = true
  try {
    const [listRes] = await Promise.all([listTasks({ page: 1, size: 30 }), loadSnapshot(), loadMapLayoutData()])
    taskList.value = listRes.data?.content || []
    if (!selectedTaskId.value) {
      const qId = Number(route.query.taskId)
      selectedTaskId.value = qId || taskList.value[0]?.id || null
    }
    if (selectedTaskId.value) await loadTaskDetails(selectedTaskId.value)
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
    if (playbackStep.value < 4) playbackStep.value += 1
    else { playbackPlaying.value = false; clearInterval(playbackTimer) }
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
        sceneParams: { baggageLocation: quickForm.origin, targetCounter: quickForm.destination }
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
.board-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
.board-header h2 { margin: 0; }
.board-header p { margin: 2px 0 0; color: #666; font-size: 13px; }
.map-toolbar { margin-bottom: 8px; }
.route-badge { background: #e6f4ff; color: #0958d9; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.map-footer { display: flex; justify-content: space-between; font-size: 12px; color: #888; margin-top: 6px; }
.stage-desc { font-size: 12px; color: #444; }
.step-pill { display: flex; align-items: center; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
.bubble-list { display: flex; flex-direction: column; gap: 10px; max-height: 260px; overflow-y: auto; }
.bubble-item { display: flex; gap: 10px; align-items: flex-start; background: #fafafa; border: 1px solid #f0f0f0; border-radius: 8px; padding: 8px 10px; }
.bubble-avatar { font-size: 24px; line-height: 1; background: #fff; border: 1px solid #e8e8e8; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.bubble-content { flex: 1; font-size: 12px; }
.bubble-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.bubble-text { color: #333; word-break: break-word; }
.geojson-import-btn { display: inline-block; cursor: pointer; }
</style>
