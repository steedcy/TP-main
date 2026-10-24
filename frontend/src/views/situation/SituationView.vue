<template>
  <section class="situation-page">
    <header class="page-header">
      <div>
        <h1>二维态势</h1>
        <p>F2 候机楼平面图 · 坐标原点位于左上角，单位为像素</p>
      </div>
      <a-space wrap>
        <a-tag color="blue">自动刷新 {{ refreshInterval }} 秒</a-tag>
        <span class="updated-at">最近更新：{{ generatedAtLabel }}</span>
        <a-button :loading="loading" @click="loadSnapshot">刷新</a-button>
      </a-space>
    </header>

    <a-alert v-if="snapshotError" type="warning" show-icon style="margin-bottom: 12px" :message="snapshotError" description="保留上次成功获取的数据；连接恢复后自动更新。" />
    <a-alert v-if="unpositionedDevices.length" type="info" show-icon style="margin-bottom: 12px"
             :message="`${unpositionedDevices.length} 个设备缺少有效坐标或超出底图范围，仅在下方列表展示`" />
    <a-card class="map-card" :body-style="{ padding: '12px' }">
      <div class="map-toolbar">
        <a-space wrap>
          <a-button aria-label="放大底图" @click="zoomBy(1.25)">＋</a-button>
          <a-button aria-label="缩小底图" @click="zoomBy(0.8)">－</a-button>
          <a-button @click="fitWidth">适应宽度</a-button>
          <a-button @click="fitAll">查看全图</a-button>
          <span class="zoom-label">{{ Math.round(zoom * 100) }}%</span>
        </a-space>
        <a-checkbox-group v-model:value="selectedTypes" class="type-filter">
          <a-checkbox v-for="type in DEVICE_TYPES" :key="type.value" :value="type.value">{{ type.label }}</a-checkbox>
        </a-checkbox-group>
        <a-space wrap class="map-legend">
          <span><i class="legend-dot online"></i>在线空闲</span>
          <span><i class="legend-dot busy"></i>在线忙碌</span>
          <span><i class="legend-dot offline"></i>离线/停用</span>
        </a-space>
      </div>

      <div
        ref="viewportRef"
        class="map-viewport"
        :class="{ dragging }"
        @wheel.prevent="handleWheel"
        @pointerdown="startPan"
        @pointermove="movePan"
        @pointerup="endPan"
        @pointercancel="endPan"
        @pointerleave="endPan"
      >
        <div
          class="map-canvas"
          :style="canvasStyle"
        >
          <img class="floorplan" src="/F2.jpg" alt="F2 候机楼平面图" draggable="false" @load="mapLoaded = true" @error="mapError = true" />
          <button
            v-for="device in positionedDevices"
            :key="device.deviceCode"
            class="device-marker"
            :class="markerClass(device)"
            :style="markerStyle(device)"
            :title="markerTitle(device)"
            @pointerdown.stop
            @click.stop="selectedDevice = device"
          >
            <span class="marker-dot"></span>
            <span class="marker-label">{{ device.deviceName || device.deviceCode }}</span>
          </button>
        </div>
        <div v-if="!mapLoaded && !mapError" class="map-message">正在加载 F2 底图…</div>
        <a-alert v-if="mapError" class="map-error" type="error" show-icon message="F2.jpg 底图加载失败" description="请确认前端静态资源目录中存在 F2.jpg。" />
        <div v-if="!devices.length && !loading && !snapshotError" class="empty-overlay">当前没有已登记的设备代理</div>
      </div>
      <div class="map-hint">按住鼠标左键拖动平移；滚动鼠标滚轮缩放；也可使用上方按钮。设备坐标按图片左上角原点同比例定位；更换底图尺寸或裁剪范围须重新标定坐标。</div>
    </a-card>

    <a-card title="仿真体及设备代理状态" class="device-card">
      <a-table :data-source="filteredDevices" :columns="columns" row-key="deviceCode" :pagination="{ pageSize: 10, showSizeChanger: false }" size="small" :scroll="{ x: 900 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            {{ deviceTypeLabel(record.simulatedDeviceType || record.deviceTypeCode) }}
            <a-tag v-if="record.simulatedDeviceType" color="cyan">仿真体</a-tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="statusColor(record)">{{ statusLabel(record) }}</a-tag>
          </template>
          <template v-else-if="column.key === 'position'">
            {{ markerPosition(record) ? `${coordinate(record.location?.x)}, ${coordinate(record.location?.y)}` : '无有效坐标' }}
          </template>
          <template v-else-if="column.key === 'lastReportedAt'">
            {{ record.lastReportedAt || '—' }}
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal v-model:open="detailOpen" :title="selectedDevice?.deviceName || '设备详情'" :footer="null">
      <a-descriptions v-if="selectedDevice" :column="1" bordered size="small">
        <a-descriptions-item label="设备编码">{{ selectedDevice.deviceCode }}</a-descriptions-item>
        <a-descriptions-item label="代理编码">{{ selectedDevice.agentId }}</a-descriptions-item>
        <a-descriptions-item label="设备类型">{{ deviceTypeLabel(selectedDevice.simulatedDeviceType || selectedDevice.deviceTypeCode) }}</a-descriptions-item>
        <a-descriptions-item label="在线/工作状态">{{ statusLabel(selectedDevice) }}</a-descriptions-item>
        <a-descriptions-item label="所属区域">{{ selectedDevice.location?.zone || '—' }}</a-descriptions-item>
        <a-descriptions-item label="坐标（左上角原点）">{{ markerPosition(selectedDevice) ? `X ${coordinate(selectedDevice.location?.x)}, Y ${coordinate(selectedDevice.location?.y)}` : '无有效坐标' }}</a-descriptions-item>
        <a-descriptions-item label="已启用能力摘要">{{ (selectedDevice.capabilityTypes || []).map(capabilityLabel).join('、') || '无已启用能力' }}</a-descriptions-item>
        <a-descriptions-item label="当前任务">
          <router-link v-if="canViewTasks && selectedDevice.currentTaskId" :to="`/tasks/${selectedDevice.currentTaskId}`">任务 {{ selectedDevice.currentTaskId }}</router-link>
          <span v-else>{{ selectedDevice.currentTaskId ?? '—' }}</span>
        </a-descriptions-item>
        <a-descriptions-item label="最后上报">{{ selectedDevice.lastReportedAt || '—' }}</a-descriptions-item>
      </a-descriptions>
    </a-modal>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import request from '../../api/request'
import { DEVICE_TYPES, deviceTypeLabel, capabilityLabel } from '../../constants/capability'
import { useAuthStore } from '../../store/auth'

const MAP_WIDTH = 1260
const MAP_HEIGHT = 6895
const viewportRef = ref(null)
const viewportSize = ref({ width: 0, height: 0 })
const devices = ref([])
const selectedTypes = ref(DEVICE_TYPES.map(type => type.value))
const canViewTasks = computed(() => ['OPERATOR', 'SYSTEM_ADMIN'].includes(useAuthStore().role))
const filteredDevices = computed(() => devices.value.filter(device => selectedTypes.value.includes(device.deviceTypeCode)
  || (device.simulatedDeviceType && selectedTypes.value.includes(device.simulatedDeviceType))))
const positionedDevices = computed(() => filteredDevices.value.filter(device => markerPosition(device)))
const unpositionedDevices = computed(() => filteredDevices.value.filter(device => !markerPosition(device)))
const loading = ref(false)
const snapshotError = ref('')
const generatedAt = ref('')
const refreshInterval = ref(5)
const zoom = ref(1)
const pan = ref({ x: 0, y: 0 })
const dragging = ref(false)
const mapLoaded = ref(false)
const mapError = ref(false)
const selectedDevice = ref(null)
const detailOpen = computed({
  get: () => Boolean(selectedDevice.value),
  set: (value) => { if (!value) selectedDevice.value = null }
})
let timer
let resizeObserver
let dragOrigin

const columns = [
  { title: '设备编码', dataIndex: 'deviceCode', width: 130 },
  { title: '设备名称', dataIndex: 'deviceName', width: 160 },
  { title: '设备类型', key: 'type', width: 190 },
  { title: '区域', key: 'area', customRender: ({ record }) => record.location?.zone || '—', width: 150 },
  { title: '在线/工作状态', key: 'status', width: 150 },
  { title: '坐标 X, Y', key: 'position', width: 150 },
  { title: '当前任务', dataIndex: 'currentTaskId', width: 110 },
  { title: '最后上报时间', key: 'lastReportedAt', width: 190 }
]

const baseWidth = computed(() => viewportSize.value.width || 900)
const baseHeight = computed(() => baseWidth.value * MAP_HEIGHT / MAP_WIDTH)
const canvasStyle = computed(() => ({
  width: `${baseWidth.value}px`,
  height: `${baseHeight.value}px`,
  transform: `translate(${pan.value.x}px, ${pan.value.y}px) scale(${zoom.value})`
}))
const generatedAtLabel = computed(() => generatedAt.value || '尚无数据')

function coordinate(value) {
  return value === null || value === undefined || value === '' ? '—' : Number(value).toFixed(1).replace(/\.0$/, '')
}

function markerPosition(device) {
  const rawX = device.location?.x
  const rawY = device.location?.y
  if (rawX === null || rawX === undefined || rawX === '' || rawY === null || rawY === undefined || rawY === '') return null
  const x = Number(rawX)
  const y = Number(rawY)
  if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || x > MAP_WIDTH || y < 0 || y > MAP_HEIGHT) return null
  return { left: x / MAP_WIDTH * 100, top: y / MAP_HEIGHT * 100 }
}

function markerStyle(device) {
  const point = markerPosition(device)
  return { left: `${point.left}%`, top: `${point.top}%` }
}

function markerClass(device) {
  if (device.agentStatus !== 'ENABLED' || device.onlineStatus !== 'ONLINE') return 'marker-offline'
  return device.workStatus === 'BUSY' ? 'marker-busy' : 'marker-online'
}

function statusLabel(device) {
  if (device.agentStatus !== 'ENABLED') return '代理停用'
  if (device.onlineStatus !== 'ONLINE') return '离线'
  return device.workStatus === 'BUSY' ? '在线·忙碌' : '在线·空闲'
}

function statusColor(device) {
  if (device.agentStatus !== 'ENABLED' || device.onlineStatus !== 'ONLINE') return 'default'
  return device.workStatus === 'BUSY' ? 'orange' : 'green'
}

function markerTitle(device) {
  return `${device.deviceName || device.deviceCode} · ${statusLabel(device)} · X ${coordinate(device.location?.x)}, Y ${coordinate(device.location?.y)}`
}

async function loadSnapshot() {
  if (loading.value) return
  loading.value = true
  try {
    const response = await request.get('/situation/snapshot', { silent: true, timeout: 10000 })
    devices.value = response.data?.agents || []
    if (selectedDevice.value) {
      selectedDevice.value = devices.value.find(device => device.deviceCode === selectedDevice.value.deviceCode) || null
    }
    generatedAt.value = response.data?.generatedAt || ''
    refreshInterval.value = Number(response.data?.refreshIntervalSeconds) || 5
    snapshotError.value = ''
  } catch (error) {
    snapshotError.value = error.response?.status === 401 ? '登录已过期，请重新登录'
      : `态势刷新失败（${new Date().toLocaleString()}），正在自动重试`
  } finally {
    loading.value = false
  }
}

function updateViewport() {
  const el = viewportRef.value
  if (el) viewportSize.value = { width: el.clientWidth, height: el.clientHeight }
}

function fitWidth() {
  zoom.value = 1
  pan.value = { x: 0, y: 0 }
}

function fitAll() {
  updateViewport()
  const ratio = Math.min(viewportSize.value.width / baseWidth.value, viewportSize.value.height / baseHeight.value)
  zoom.value = Math.max(0.05, Math.min(1, ratio))
  pan.value = { x: Math.max(0, (viewportSize.value.width - baseWidth.value * zoom.value) / 2), y: Math.max(0, (viewportSize.value.height - baseHeight.value * zoom.value) / 2) }
}

function zoomAt(nextZoom, clientX, clientY) {
  const el = viewportRef.value
  const rect = el?.getBoundingClientRect()
  const target = Math.max(0.08, Math.min(8, nextZoom))
  if (!rect) { zoom.value = target; return }
  const px = clientX - rect.left
  const py = clientY - rect.top
  const imageX = (px - pan.value.x) / zoom.value
  const imageY = (py - pan.value.y) / zoom.value
  zoom.value = target
  pan.value = { x: px - imageX * target, y: py - imageY * target }
}

function zoomBy(factor) {
  const rect = viewportRef.value?.getBoundingClientRect()
  if (rect) zoomAt(zoom.value * factor, rect.left + rect.width / 2, rect.top + rect.height / 2)
}

function handleWheel(event) {
  zoomAt(zoom.value * (event.deltaY < 0 ? 1.12 : 1 / 1.12), event.clientX, event.clientY)
}

function startPan(event) {
  if (event.button !== 0) return
  dragging.value = true
  dragOrigin = { x: event.clientX, y: event.clientY, panX: pan.value.x, panY: pan.value.y }
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function movePan(event) {
  if (!dragging.value || !dragOrigin) return
  pan.value = { x: dragOrigin.panX + event.clientX - dragOrigin.x, y: dragOrigin.panY + event.clientY - dragOrigin.y }
}

function endPan() {
  dragging.value = false
  dragOrigin = null
}

onMounted(() => {
  updateViewport()
  resizeObserver = new ResizeObserver(updateViewport)
  if (viewportRef.value) resizeObserver.observe(viewportRef.value)
  loadSnapshot()
  timer = window.setInterval(loadSnapshot, refreshInterval.value * 1000)
})

onUnmounted(() => {
  window.clearInterval(timer)
  resizeObserver?.disconnect()
})
</script>

<style scoped>
.situation-page { display: flex; flex-direction: column; gap: 16px; }
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.page-header h1 { margin: 0 0 4px; font-size: 22px; }
.page-header p, .updated-at { margin: 0; color: #777; }
.map-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; flex-wrap: wrap; }
.zoom-label { min-width: 54px; color: #555; text-align: right; }
.map-legend { color: #555; font-size: 13px; }
.map-legend span { display: inline-flex; align-items: center; gap: 5px; }
.legend-dot, .marker-dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; border: 2px solid white; box-shadow: 0 1px 4px #5558; }
.online .legend-dot, .legend-dot.online { background: #16a34a; }
.legend-dot.busy { background: #f59e0b; }
.legend-dot.offline { background: #8b9098; }
.map-viewport { position: relative; height: min(68vh, 760px); min-height: 420px; overflow: hidden; background: #e9edf2; border: 1px solid #d9d9d9; border-radius: 4px; cursor: grab; touch-action: none; }
.map-viewport.dragging { cursor: grabbing; }
.map-canvas { position: absolute; left: 0; top: 0; transform-origin: 0 0; user-select: none; }
.floorplan { display: block; width: 100%; height: 100%; object-fit: fill; pointer-events: none; }
.device-marker { position: absolute; z-index: 2; transform: translate(-50%, -50%); padding: 0; border: 0; background: transparent; cursor: pointer; white-space: nowrap; }
.marker-dot { width: 14px; height: 14px; border-width: 2px; }
.marker-online .marker-dot { background: #16a34a; }
.marker-busy .marker-dot { background: #f59e0b; }
.marker-offline .marker-dot { background: #8b9098; }
.marker-label { display: block; margin-top: 2px; padding: 1px 4px; border-radius: 3px; color: #17202a; background: #ffffffdf; font-size: 11px; line-height: 1.25; }
.map-message, .empty-overlay { position: absolute; z-index: 3; left: 50%; top: 50%; transform: translate(-50%, -50%); padding: 10px 16px; color: #555; background: #fffE; border-radius: 4px; box-shadow: 0 1px 6px #0002; pointer-events: none; }
.empty-overlay { top: 24px; transform: translateX(-50%); }
.map-error { position: absolute; z-index: 4; left: 12px; right: 12px; top: 12px; }
.map-hint { margin-top: 8px; color: #777; font-size: 12px; }
.device-card :deep(.ant-card-head-title) { font-weight: 600; }
@media (max-width: 700px) { .map-viewport { min-height: 360px; height: 55vh; } .page-header { align-items: flex-start; } }
</style>
