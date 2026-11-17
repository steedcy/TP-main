<template>
  <div class="indoor-map-wrapper">
    <div ref="mapContainerRef" class="leaflet-container-box"></div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import '@geoman-io/leaflet-geoman-free'
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css'
import { MAP_HEIGHT, MAP_WIDTH, POI_CATEGORIES, parseRegionGeometry } from '../utils/terminalMap'

const props = defineProps({
  editable: { type: Boolean, default: false },
  pois: { type: Array, default: () => [] },
  regions: { type: Array, default: () => [] },
  devices: { type: Array, default: () => [] },
  passengerPoint: { type: Object, default: null },
  routePoints: { type: Array, default: () => [] },
  stopPoints: { type: Array, default: () => [] },
  collabEdges: { type: Array, default: () => [] },
  activeDeviceStepMap: { type: Object, default: () => ({}) },
  stepBubbles: { type: Array, default: () => [] },
  showPois: { type: Boolean, default: true },
  showRegions: { type: Boolean, default: true },
  showRoute: { type: Boolean, default: true },
  showCollabLinks: { type: Boolean, default: true },
  showDeviceBubbles: { type: Boolean, default: true },
  pickPassengerMode: { type: Boolean, default: false }
})

const emit = defineEmits([
  'cursor-move',
  'pick-passenger',
  'poi-click',
  'create-poi',
  'update-poi',
  'delete-poi',
  'create-region',
  'update-region',
  'delete-region'
])

const mapContainerRef = ref(null)
let map = null
let regionsGroup = null
let poisGroup = null
let routeGroup = null
let collabGroup = null
let devicesGroup = null
let bubblesGroup = null
let passengerGroup = null

function toLatLng(x, y) {
  return [MAP_HEIGHT - Number(y), Number(x)]
}

function fromLatLng(ll) {
  return {
    x: Math.max(0, Math.min(MAP_WIDTH, Math.round(ll.lng))),
    y: Math.max(0, Math.min(MAP_HEIGHT, Math.round(MAP_HEIGHT - ll.lat)))
  }
}

function poiColor(cat) {
  return POI_CATEGORIES.find(c => c.key === cat)?.color || '#1677ff'
}

function poiBadge(cat) {
  return POI_CATEGORIES.find(c => c.key === cat)?.badge || '点'
}

function syncRegionsLayer() {
  if (!regionsGroup) return
  regionsGroup.clearLayers()
  if (!props.showRegions) return

  for (const reg of props.regions) {
    const pts = parseRegionGeometry(reg)
    if (!pts.length) continue
    const latlngs = pts.map(p => toLatLng(p.x, p.y))
    let layer = null
    if (reg.regionType === 'CORRIDOR' && latlngs.length >= 2) {
      layer = L.polyline(latlngs, {
        color: '#13c2c2',
        weight: 8,
        opacity: 0.65
      })
    } else if (latlngs.length >= 3) {
      const isIso = reg.regionType === 'ISOLATED_ZONE'
      layer = L.polygon(latlngs, {
        color: isIso ? '#722ed1' : '#389e0d',
        fillColor: isIso ? '#722ed1' : '#52c41a',
        fillOpacity: 0.16,
        weight: 2,
        dashArray: '6 5'
      })
    }
    if (!layer) continue
    layer._tipMeta = { kind: 'region', data: reg }
    const prefix = reg.regionType === 'ISOLATED_ZONE' ? '候机隔离区' : reg.regionType === 'CHECKIN_HALL' ? '值机办理区' : '走廊通道'
    layer.bindTooltip(`${prefix}：${reg.regionName}`, { sticky: true })
    layer.on('pm:edit', () => {
      const raw = layer.getLatLngs()
      const ring = Array.isArray(raw[0]) ? raw[0] : raw
      emit('update-region', {
        id: reg.id,
        regionName: reg.regionName,
        regionType: reg.regionType,
        points: ring.map(fromLatLng)
      })
    })
    layer.on('pm:dragend', () => {
      const raw = layer.getLatLngs()
      const ring = Array.isArray(raw[0]) ? raw[0] : raw
      emit('update-region', {
        id: reg.id,
        regionName: reg.regionName,
        regionType: reg.regionType,
        points: ring.map(fromLatLng)
      })
    })
    regionsGroup.addLayer(layer)
  }
}

function syncPoisLayer() {
  if (!poisGroup) return
  poisGroup.clearLayers()
  if (!props.showPois) return

  for (const poi of props.pois) {
    const icon = L.divIcon({
      className: 'leaflet-poi-wrapper',
      html: `<div class="leaflet-poi-pill" style="--poi-color:${poiColor(poi.category)}">
        <span class="dot">${poiBadge(poi.category)}</span>
        <span class="txt">${poi.poiName}</span>
      </div>`,
      iconSize: [0, 0],
      iconAnchor: [0, 0]
    })
    const marker = L.marker(toLatLng(poi.x, poi.y), { icon })
    marker._tipMeta = { kind: 'poi', data: poi }
    marker.on('click', () => {
      if (props.pickPassengerMode) {
        emit('pick-passenger', { x: Number(poi.x), y: Number(poi.y), label: poi.poiName, code: poi.poiCode })
      } else {
        emit('poi-click', poi)
      }
    })
    marker.on('pm:dragend', () => {
      if (!poi.id) return
      const pt = fromLatLng(marker.getLatLng())
      emit('update-poi', { ...poi, x: pt.x, y: pt.y })
    })
    poisGroup.addLayer(marker)
  }
}

function syncRouteLayer() {
  if (!routeGroup) return
  routeGroup.clearLayers()
  if (!props.showRoute || props.routePoints.length < 2) return

  const latlngs = props.routePoints.map(p => toLatLng(p.x, p.y))
  routeGroup.addLayer(L.polyline(latlngs, { color: '#1677ff', weight: 9, opacity: 0.25, pmIgnore: true }))
  routeGroup.addLayer(L.polyline(latlngs, {
    color: '#1677ff',
    weight: 4,
    dashArray: '12 8',
    className: 'leaflet-route-animated',
    pmIgnore: true
  }))
  props.stopPoints.forEach((pt, idx) => {
    const icon = L.divIcon({
      className: 'leaflet-stop-wrapper',
      html: `<div class="leaflet-stop-badge">${idx + 1}</div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    })
    routeGroup.addLayer(L.marker(toLatLng(pt.x, pt.y), { icon, interactive: false, pmIgnore: true }))
  })
}

function syncCollabLayer() {
  if (!collabGroup) return
  collabGroup.clearLayers()
  if (!props.showCollabLinks) return
  for (const edge of props.collabEdges) {
    collabGroup.addLayer(L.polyline([toLatLng(edge.x1, edge.y1), toLatLng(edge.x2, edge.y2)], {
      color: '#fa8c16',
      weight: 3,
      dashArray: '8 6',
      opacity: 0.8,
      pmIgnore: true
    }))
  }
}

function syncDevicesLayer() {
  if (!devicesGroup) return
  devicesGroup.clearLayers()
  for (const d of props.devices) {
    if (!d.location || !Number.isFinite(Number(d.location.x)) || !Number.isFinite(Number(d.location.y))) continue
    const isBusy = d.workStatus === 'BUSY' || Boolean(props.activeDeviceStepMap[d.agentId])
    const cls = d.onlineStatus !== 'ONLINE' ? 'offline' : isBusy ? 'busy' : 'online'
    const stepText = props.activeDeviceStepMap[d.agentId] ? ` · 执行第${props.activeDeviceStepMap[d.agentId]}步` : ''
    const icon = L.divIcon({
      className: 'leaflet-dev-wrapper',
      html: `<div class="leaflet-dev-pill ${cls}"><span class="dot"></span><span class="txt">${d.deviceName}${stepText}</span></div>`,
      iconSize: [0, 0],
      iconAnchor: [0, 0]
    })
    devicesGroup.addLayer(L.marker(toLatLng(d.location.x, d.location.y), { icon, pmIgnore: true }))
  }
}

function syncPassengerLayer() {
  if (!passengerGroup) return
  passengerGroup.clearLayers()
  if (!props.passengerPoint) return
  const icon = L.divIcon({
    className: 'leaflet-pax-wrapper',
    html: `<div class="leaflet-pax-pill"><span class="pulse"></span><span class="ico">🧑</span><span class="txt">旅客位置：${props.passengerPoint.label}</span></div>`,
    iconSize: [0, 0],
    iconAnchor: [0, 0]
  })
  passengerGroup.addLayer(L.marker(toLatLng(props.passengerPoint.x, props.passengerPoint.y), { icon, pmIgnore: true }))
}

function syncBubblesLayer() {
  if (!bubblesGroup) return
  bubblesGroup.clearLayers()
  if (!props.showDeviceBubbles || !props.stepBubbles.length) return

  const devByAgent = new Map()
  for (const d of props.devices) {
    if (d.agentId) devByAgent.set(d.agentId, d)
  }
  const perDeviceCount = new Map()

  for (const b of props.stepBubbles) {
    const dev = devByAgent.get(b.agentCode)
    if (!dev?.location || !Number.isFinite(Number(dev.location.x)) || !Number.isFinite(Number(dev.location.y))) continue
    const idx = perDeviceCount.get(b.agentCode) || 0
    perDeviceCount.set(b.agentCode, idx + 1)
    const offsetY = -36 - idx * 84
    const activeCls = b.isActive ? 'active' : b.status === 'SKIPPED' || b.status === 'FAILED' ? 'warn' : 'done'
    const statusText = b.isActive ? '执行中' : b.statusText
    const feedbackHtml = b.feedbackText && !b.isActive
      ? `<div class="mb-row fb"><span>回执：</span>${b.feedbackText}</div>`
      : ''
    const icon = L.divIcon({
      className: 'leaflet-map-bubble-wrapper',
      html: `<div class="leaflet-map-bubble ${activeCls}" style="transform: translate(16px, ${offsetY}px);">
        <div class="mb-head">
          <span>${b.icon} 第${b.stepSeq}步 · ${b.deviceLabel}</span>
          <span class="mb-tag">${statusText}</span>
        </div>
        <div class="mb-row cmd"><span>指令：</span>${b.commandText}</div>
        ${feedbackHtml}
      </div>`,
      iconSize: [0, 0],
      iconAnchor: [0, 0]
    })
    bubblesGroup.addLayer(L.marker(toLatLng(dev.location.x, dev.location.y), { icon, interactive: false, pmIgnore: true }))
  }
}

function focusActiveArea() {
  if (!map) return
  map.fitBounds([[MAP_HEIGHT - 3880, 260], [MAP_HEIGHT - 2080, 1060]])
}

function fitAll() {
  if (!map) return
  map.fitBounds([[0, 0], [MAP_HEIGHT, MAP_WIDTH]])
}

function exportGeoJson() {
  const features = []
  for (const poi of props.pois) {
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [Number(poi.x), Number(poi.y)] },
      properties: { kind: 'POI', poiCode: poi.poiCode, poiName: poi.poiName, category: poi.category, zone: poi.zone || '' }
    })
  }
  for (const reg of props.regions) {
    const pts = parseRegionGeometry(reg).map(p => [Number(p.x), Number(p.y)])
    if (reg.regionType === 'CORRIDOR' && pts.length >= 2) {
      features.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: pts },
        properties: { kind: 'REGION', regionCode: reg.regionCode, regionName: reg.regionName, regionType: reg.regionType }
      })
    } else if (pts.length >= 3) {
      features.push({
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [[...pts, pts[0]]] },
        properties: { kind: 'REGION', regionCode: reg.regionCode, regionName: reg.regionName, regionType: reg.regionType }
      })
    }
  }
  return { type: 'FeatureCollection', features }
}

onMounted(() => {
  map = L.map(mapContainerRef.value, {
    crs: L.CRS.Simple,
    minZoom: -3,
    maxZoom: 2,
    zoomSnap: 0.25,
    attributionControl: false
  })
  L.imageOverlay('/F2.jpg', [[0, 0], [MAP_HEIGHT, MAP_WIDTH]]).addTo(map)

  regionsGroup = L.layerGroup().addTo(map)
  collabGroup = L.layerGroup().addTo(map)
  routeGroup = L.layerGroup().addTo(map)
  poisGroup = L.layerGroup().addTo(map)
  devicesGroup = L.layerGroup().addTo(map)
  bubblesGroup = L.layerGroup().addTo(map)
  passengerGroup = L.layerGroup().addTo(map)

  focusActiveArea()

  if (props.editable) {
    map.pm.setLang('zh')
    map.pm.setGlobalOptions({
      snappable: true,
      snapDistance: 18,
      snapMiddle: true,
      allowSelfIntersection: false
    })
    map.pm.addControls({
      position: 'topleft',
      drawMarker: true,
      drawPolyline: true,
      drawPolygon: true,
      drawRectangle: true,
      drawCircle: false,
      drawCircleMarker: false,
      drawText: false,
      editMode: true,
      dragMode: true,
      cutPolygon: false,
      removalMode: true,
      rotateMode: false
    })

    map.on('pm:create', (e) => {
      const layer = e.layer
      if (e.shape === 'Marker') {
        const pt = fromLatLng(layer.getLatLng())
        map.removeLayer(layer)
        emit('create-poi', pt)
      } else if (e.shape === 'Line') {
        const pts = layer.getLatLngs().map(fromLatLng)
        map.removeLayer(layer)
        emit('create-region', { regionType: 'CORRIDOR', points: pts })
      } else {
        const raw = layer.getLatLngs()
        const ring = Array.isArray(raw[0]) ? raw[0] : raw
        const pts = ring.map(fromLatLng)
        map.removeLayer(layer)
        emit('create-region', { regionType: 'ISOLATED_ZONE', points: pts })
      }
    })

    map.on('pm:remove', (e) => {
      const meta = e.layer?._tipMeta
      if (!meta) return
      if (meta.kind === 'poi' && meta.data?.id) emit('delete-poi', meta.data.id)
      if (meta.kind === 'region' && meta.data?.id) emit('delete-region', meta.data.id)
    })
  }

  map.on('mousemove', (e) => {
    const pt = fromLatLng(e.latlng)
    emit('cursor-move', pt)
  })

  map.on('click', (e) => {
    if (!props.pickPassengerMode) return
    const pt = fromLatLng(e.latlng)
    emit('pick-passenger', pt)
  })

  syncRegionsLayer()
  syncPoisLayer()
  syncRouteLayer()
  syncCollabLayer()
  syncDevicesLayer()
  syncBubblesLayer()
  syncPassengerLayer()
})

watch(() => [props.regions, props.showRegions], syncRegionsLayer, { deep: true })
watch(() => [props.pois, props.showPois], syncPoisLayer, { deep: true })
watch(() => [props.routePoints, props.stopPoints, props.showRoute], syncRouteLayer, { deep: true })
watch(() => [props.collabEdges, props.showCollabLinks], syncCollabLayer, { deep: true })
watch(() => [props.devices, props.activeDeviceStepMap], syncDevicesLayer, { deep: true })
watch(() => [props.stepBubbles, props.devices, props.showDeviceBubbles], syncBubblesLayer, { deep: true })
watch(() => props.passengerPoint, syncPassengerLayer, { deep: true })

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})

defineExpose({ fitAll, focusActiveArea, exportGeoJson })
</script>

<style scoped>
.indoor-map-wrapper {
  width: 100%;
  height: 620px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f5f5;
}
.leaflet-container-box {
  width: 100%;
  height: 100%;
}
</style>

<style>
.leaflet-poi-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transform: translate(-11px, -11px);
  white-space: nowrap;
  cursor: pointer;
}
.leaflet-poi-pill .dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--poi-color);
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.28);
}
.leaflet-poi-pill .txt {
  background: rgba(255,255,255,0.92);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #262626;
  border: 1px solid #d9d9d9;
}
.leaflet-dev-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transform: translate(-8px, -8px);
  white-space: nowrap;
}
.leaflet-dev-pill .dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0,0,0,0.35);
}
.leaflet-dev-pill.online .dot { background: #52c41a; }
.leaflet-dev-pill.busy .dot { background: #fa8c16; animation: lfPulse 1.2s infinite; }
.leaflet-dev-pill.offline .dot { background: #8c8c8c; }
.leaflet-dev-pill .txt {
  background: rgba(0,0,0,0.78);
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}
.leaflet-pax-pill {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  transform: translate(-50%, -50%);
  white-space: nowrap;
}
.leaflet-pax-pill .ico { font-size: 22px; position: relative; z-index: 2; }
.leaflet-pax-pill .txt {
  background: #1677ff;
  color: #fff;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
}
.leaflet-pax-pill .pulse {
  position: absolute;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(22, 119, 255, 0.28);
  animation: lfPulse 1.5s infinite;
}
.leaflet-stop-badge {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #1677ff;
  color: #fff;
  border: 2px solid #fff;
  font-size: 12px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3);
}
.leaflet-route-animated {
  animation: lfDash 1.2s linear infinite;
}
.leaflet-map-bubble {
  width: 248px;
  background: rgba(255, 255, 255, 0.96);
  border: 2px solid #1677ff;
  border-radius: 8px;
  padding: 6px 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.22);
  font-size: 11px;
  line-height: 1.4;
  color: #262626;
  pointer-events: none;
}
.leaflet-map-bubble.active {
  border-color: #fa8c16;
  box-shadow: 0 0 0 4px rgba(250, 140, 22, 0.25), 0 6px 14px rgba(0, 0, 0, 0.28);
}
.leaflet-map-bubble.done {
  border-color: #52c41a;
}
.leaflet-map-bubble.warn {
  border-color: #ff4d4f;
}
.leaflet-map-bubble .mb-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 700;
  margin-bottom: 3px;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 2px;
}
.leaflet-map-bubble .mb-tag {
  font-size: 10px;
  padding: 0 5px;
  border-radius: 4px;
  background: #e6f4ff;
  color: #0958d9;
}
.leaflet-map-bubble.active .mb-tag { background: #fff7e6; color: #d46b08; }
.leaflet-map-bubble.done .mb-tag { background: #f6ffed; color: #389e0d; }
.leaflet-map-bubble.warn .mb-tag { background: #fff2f0; color: #cf1322; }
.leaflet-map-bubble .mb-row {
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.leaflet-map-bubble .mb-row.cmd span { color: #0958d9; font-weight: 600; }
.leaflet-map-bubble .mb-row.fb span { color: #389e0d; font-weight: 600; }
@keyframes lfDash {
  to { stroke-dashoffset: -40; }
}
@keyframes lfPulse {
  0% { transform: scale(1); opacity: 0.9; }
  70% { transform: scale(1.6); opacity: 0.2; }
  100% { transform: scale(1); opacity: 0.9; }
}
</style>
