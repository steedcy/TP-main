export const MAP_WIDTH = 1260
export const MAP_HEIGHT = 6895

export const POI_CATEGORIES = [
  { key: 'GATE', label: '登机口', color: '#1677ff', badge: '登' },
  { key: 'CHECKIN', label: '值机柜台', color: '#13c2c2', badge: '值' },
  { key: 'BAGGAGE', label: '行李托运柜台', color: '#fa8c16', badge: '托' },
  { key: 'SECURITY', label: '安检通道', color: '#722ed1', badge: '安' },
  { key: 'MEASURE', label: '智能行李测量点', color: '#eb2f96', badge: '测' },
  { key: 'SERVICE', label: '服务柜台', color: '#52c41a', badge: '服' }
]

export const DEFAULT_TERMINAL_POIS = [
  { poiCode: 'T2值机岛A01', poiName: 'T2值机岛 A01', category: 'CHECKIN', x: 400, y: 3100, zone: 'T2值机区-北' },
  { poiCode: 'T2值机岛A03', poiName: 'T2值机岛 A03', category: 'CHECKIN', x: 805, y: 4050, zone: 'T2值机区-南' },
  { poiCode: 'T2值机区', poiName: 'T2值机区（会合点）', category: 'CHECKIN', x: 805, y: 4050, zone: 'T2值机区-南' },
  { poiCode: '行李托运柜台A01', poiName: '行李托运柜台 A01', category: 'BAGGAGE', x: 430, y: 3180, zone: '行李托运区' },
  { poiCode: '超规行李专柜B01', poiName: '超规行李专柜 B01', category: 'BAGGAGE', x: 810, y: 4200, zone: '超规行李专柜区' },
  { poiCode: '安检通道01', poiName: '安检通道 01', category: 'SECURITY', x: 630, y: 3750, zone: '中央安检区' },
  { poiCode: 'VIP安检通道', poiName: 'VIP 特殊旅客安检通道', category: 'SECURITY', x: 840, y: 3750, zone: '中央安检区' },
  { poiCode: '智能行李测量点A', poiName: '智能行李测量点（主）', category: 'MEASURE', x: 400, y: 3106, zone: 'T2值机区-北', linkedDeviceCode: 'SIM_F2_BAGGAGE' },
  { poiCode: '智能行李测量点B', poiName: '智能行李测量点（备）', category: 'MEASURE', x: 465, y: 3447, zone: 'T2值机区-中', linkedDeviceCode: 'SIM_F2_BAGGAGE_B' },
  { poiCode: '旅客服务中心', poiName: '旅客综合服务柜台', category: 'SERVICE', x: 630, y: 4150, zone: 'F2中庭南区' },
  { poiCode: 'GATE_A01', poiName: '登机口 A01', category: 'GATE', x: 500, y: 4600, zone: 'A指廊' },
  { poiCode: 'GATE_A05', poiName: '登机口 A05', category: 'GATE', x: 815, y: 4600, zone: 'A指廊' },
  { poiCode: 'GATE_B01', poiName: '登机口 B01', category: 'GATE', x: 420, y: 5200, zone: 'B指廊' }
]

const DEFAULT_CORRIDOR_NODES = [
  { id: 'N_WEST_TOP', x: 430, y: 3100 },
  { id: 'N_EAST_TOP', x: 870, y: 3100 },
  { id: 'N_WEST_MID', x: 465, y: 3450 },
  { id: 'N_EAST_MID', x: 840, y: 3450 },
  { id: 'N_SEC_W', x: 630, y: 3750 },
  { id: 'N_SEC_M', x: 740, y: 3750 },
  { id: 'N_SEC_E', x: 840, y: 3750 },
  { id: 'N_HUB_W', x: 630, y: 4100 },
  { id: 'N_HUB_E', x: 810, y: 4100 },
  { id: 'N_GATE_A_W', x: 500, y: 4520 },
  { id: 'N_GATE_A_M', x: 630, y: 4520 },
  { id: 'N_GATE_A_E', x: 815, y: 4520 },
  { id: 'N_GATE_B_W', x: 420, y: 5120 },
  { id: 'N_GATE_B_M', x: 620, y: 5120 },
  { id: 'N_GATE_B_E', x: 820, y: 5120 }
]

const DEFAULT_CORRIDOR_EDGES = [
  ['N_WEST_TOP', 'N_EAST_TOP'],
  ['N_WEST_TOP', 'N_WEST_MID'],
  ['N_EAST_TOP', 'N_EAST_MID'],
  ['N_WEST_MID', 'N_EAST_MID'],
  ['N_WEST_MID', 'N_SEC_W'],
  ['N_EAST_MID', 'N_SEC_E'],
  ['N_SEC_W', 'N_SEC_M'],
  ['N_SEC_M', 'N_SEC_E'],
  ['N_SEC_W', 'N_HUB_W'],
  ['N_SEC_E', 'N_HUB_E'],
  ['N_HUB_W', 'N_HUB_E'],
  ['N_HUB_W', 'N_GATE_A_M'],
  ['N_HUB_E', 'N_GATE_A_E'],
  ['N_GATE_A_W', 'N_GATE_A_M'],
  ['N_GATE_A_M', 'N_GATE_A_E'],
  ['N_GATE_A_W', 'N_GATE_B_W'],
  ['N_GATE_A_M', 'N_GATE_B_M'],
  ['N_GATE_A_E', 'N_GATE_B_E'],
  ['N_GATE_B_W', 'N_GATE_B_M'],
  ['N_GATE_B_M', 'N_GATE_B_E']
]

function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function pointInPolygon(pt, polygon) {
  let inside = false
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x, yi = polygon[i].y
    const xj = polygon[j].x, yj = polygon[j].y
    const intersect = ((yi > pt.y) !== (yj > pt.y)) &&
      (pt.x < (xj - xi) * (pt.y - yi) / ((yj - yi) || 1e-9) + xi)
    if (intersect) inside = !inside
  }
  return inside
}

function segmentCrossesPolygons(a, b, polygons) {
  if (!polygons.length) return false
  const samples = 6
  for (let s = 0; s <= samples; s++) {
    const t = s / samples
    const pt = { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }
    if (polygons.some(poly => poly.length >= 3 && pointInPolygon(pt, poly))) {
      return true
    }
  }
  return false
}

export function parseRegionGeometry(region) {
  try {
    const parsed = typeof region.geometryJson === 'string' ? JSON.parse(region.geometryJson) : region.geometryJson
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function resolveLocation(input, pois = DEFAULT_TERMINAL_POIS, devices = []) {
  if (!input) return null
  if (typeof input === 'object' && Number.isFinite(Number(input.x)) && Number.isFinite(Number(input.y))) {
    return { x: Number(input.x), y: Number(input.y), label: input.label || '自定义位置' }
  }
  const text = String(input).trim()
  const aliases = { F2_SERVICE_POINT: '超规行李专柜B01', F2_BAGGAGE_POINT: 'T2值机区', F2_TEST_GATE: 'GATE_A05' }
  const normalized = aliases[text] || text

  const exact = pois.find(p => p.poiCode === normalized || p.poiName === normalized)
  if (exact) return { x: Number(exact.x), y: Number(exact.y), label: exact.poiName, code: exact.poiCode }

  const fuzzy = pois.find(p => normalized.includes(p.poiCode) || p.poiCode.includes(normalized))
  if (fuzzy) return { x: Number(fuzzy.x), y: Number(fuzzy.y), label: fuzzy.poiName, code: fuzzy.poiCode }

  const dev = devices.find(d => d.deviceCode === text || d.deviceName === text)
  if (dev && dev.location && Number.isFinite(Number(dev.location.x)) && Number.isFinite(Number(dev.location.y))) {
    return { x: Number(dev.location.x), y: Number(dev.location.y), label: dev.deviceName || dev.deviceCode, code: dev.deviceCode }
  }
  return null
}

export function nearestPoi(x, y, pois = DEFAULT_TERMINAL_POIS) {
  let best = null
  let bestDist = Infinity
  for (const poi of pois) {
    const d = Math.hypot(Number(poi.x) - x, Number(poi.y) - y)
    if (d < bestDist) {
      bestDist = d
      best = poi
    }
  }
  return best ? { ...best, x: Number(best.x), y: Number(best.y), distance: Math.round(bestDist) } : null
}

function buildCorridorGraph(regions = []) {
  const customCorridors = regions.filter(r => r.regionType === 'CORRIDOR')
  const isolatedPolygons = regions
    .filter(r => r.regionType === 'ISOLATED_ZONE')
    .map(parseRegionGeometry)
    .filter(pts => pts.length >= 3)

  let nodes = []
  let edges = []

  if (customCorridors.length > 0) {
    let idx = 0
    const corridorGroups = []
    for (const c of customCorridors) {
      const pts = parseRegionGeometry(c)
      const groupIds = []
      for (let i = 0; i < pts.length; i++) {
        const nid = `C_${idx++}`
        nodes.push({ id: nid, x: Number(pts[i].x), y: Number(pts[i].y) })
        groupIds.push(nid)
        if (i > 0) edges.push([groupIds[i - 1], nid])
      }
      corridorGroups.push(groupIds)
    }
    // 自动连接相邻走廊的接近节点（<= 120px）以便跨走廊换乘
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (dist(nodes[i], nodes[j]) <= 120) {
          edges.push([nodes[i].id, nodes[j].id])
        }
      }
    }
  } else {
    nodes = DEFAULT_CORRIDOR_NODES
    edges = DEFAULT_CORRIDOR_EDGES
  }

  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]))
  const adj = Object.fromEntries(nodes.map(n => [n.id, []]))
  for (const [u, v] of edges) {
    const nu = nodeMap[u], nv = nodeMap[v]
    if (!nu || !nv) continue
    if (segmentCrossesPolygons(nu, nv, isolatedPolygons)) continue
    const w = dist(nu, nv)
    adj[u].push({ to: v, w })
    adj[v].push({ to: u, w })
  }
  return { nodes, nodeMap, adj }
}

function dijkstraPath(graph, startNodeId, endNodeId) {
  const { nodes, nodeMap, adj } = graph
  const d = Object.fromEntries(nodes.map(n => [n.id, Infinity]))
  const prev = {}
  const visited = new Set()
  d[startNodeId] = 0

  while (visited.size < nodes.length) {
    let cur = null
    let curDist = Infinity
    for (const n of nodes) {
      if (!visited.has(n.id) && d[n.id] < curDist) {
        cur = n.id
        curDist = d[n.id]
      }
    }
    if (!cur || cur === endNodeId) break
    visited.add(cur)
    for (const edge of adj[cur] || []) {
      if (!visited.has(edge.to) && d[cur] + edge.w < d[edge.to]) {
        d[edge.to] = d[cur] + edge.w
        prev[edge.to] = cur
      }
    }
  }
  if (!Number.isFinite(d[endNodeId])) return []
  const chain = []
  let p = endNodeId
  while (p) {
    chain.unshift(nodeMap[p])
    p = prev[p]
  }
  return chain
}

function nearestCorridorNode(nodes, point) {
  let best = nodes[0]
  let bestD = Infinity
  for (const n of nodes) {
    const d = dist(n, point)
    if (d < bestD) {
      bestD = d
      best = n
    }
  }
  return best
}

export function computeTerminalRoute(stops, regions = []) {
  const resolved = stops.filter(Boolean)
  if (resolved.length < 2) return { points: resolved, totalPixels: 0 }

  const graph = buildCorridorGraph(regions)
  if (!graph.nodes.length) return { points: resolved, totalPixels: 0 }

  const points = []
  let totalPixels = 0
  for (let i = 0; i < resolved.length - 1; i++) {
    const a = resolved[i]
    const b = resolved[i + 1]
    const nStart = nearestCorridorNode(graph.nodes, a)
    const nEnd = nearestCorridorNode(graph.nodes, b)
    const corridor = dijkstraPath(graph, nStart.id, nEnd.id)
    const segment = corridor.length ? [a, ...corridor, b] : [a, b]
    for (const pt of segment) {
      const last = points[points.length - 1]
      if (!last || Math.hypot(last.x - pt.x, last.y - pt.y) > 4) {
        if (last) totalPixels += Math.hypot(last.x - pt.x, last.y - pt.y)
        points.push({ x: pt.x, y: pt.y, label: pt.label || null })
      } else if (pt.label && !last.label) {
        last.label = pt.label
      }
    }
  }
  return { points, totalPixels: Math.round(totalPixels) }
}

// ===== 全面中文化与高可读性转换工具 =====

export function translateTaskFamily(family) {
  const map = {
    FLIGHT_CHANGE_RESPONSE: '航班变更应对场景',
    OVERSIZE_BAGGAGE_HANDLING: '超规行李处置场景',
    SPECIAL_PASSENGER_SERVICE: '特殊旅客协同服务场景'
  }
  return map[family] || family || '通用协同任务'
}

export function translateChangeType(type) {
  const map = {
    DELAY: '航班延误',
    EARLY: '航班提前',
    GATE_CHANGE: '登机口变更',
    CANCEL: '航班取消'
  }
  return map[type] || type || '状态变更'
}

export function translateStepStatus(status) {
  const map = {
    PENDING_ASSIGNMENT: '待分派设备',
    DISPATCHED: '已下发执行中',
    EXECUTING: '设备执行中',
    COMPLETED: '已完成',
    SKIPPED: '已跳过（未覆盖）',
    FAILED: '执行失败'
  }
  return map[status] || status || '未知状态'
}

export function translateReasonCode(code) {
  if (!code) return ''
  const map = {
    DEVICE_SUCCESS: '设备执行成功',
    NO_ONLINE_IDLE_CANDIDATE: '当前无在线空闲可用设备',
    ESCORT_CHANNEL_UNAVAILABLE: '移动服务机器人渠道不可用',
    FLIGHT_CHANNEL_UNAVAILABLE: '航班变更发布渠道不可用',
    RULE_RESOURCE_CRITICAL: '可用备用设备不足（低于安全阈值）',
    RULE_ESCORT_SPECIAL_PASSENGER: '特殊旅客机器人陪同命中高风险保护规则',
    BAGGAGE_WITHIN_LIMIT: '行李尺寸与重量均在正常限额内',
    MEASUREMENT_EVENT_REUSED: '已直接复用测量事件样本',
    ARRIVED: '已抵达目标地点'
  }
  return map[code] || code
}

export function formatReadableCommand(cap, params) {
  if (!params || !Object.keys(params).length) return ''
  if (cap === 'CAP_FLIGHT_UPDATE') {
    const typeLabel = translateChangeType(params.updateType)
    return `航延屏公告：航班 ${params.flightNumber || '—'}【${typeLabel}】，${params.updateContent || '请留意登机口提示'}`
  }
  if (cap === 'CAP_INFO_DISPLAY') {
    return `智慧航显屏幕展示：“${params.displayContent || params.message || '请按引导前往'}”`
  }
  if (cap === 'CAP_NOTIFICATION') {
    return `现场语音/人员通知：“${params.notifyContent || params.message || '请协助引导旅客'}”`
  }
  if (cap === 'CAP_NAVIGATION') {
    return `移动引导至目的地：【${params.targetLocation || '指定区域'}】`
  }
  if (cap === 'CAP_ESCORT') {
    return `陪同护送旅客前往：【${params.targetLocation || '指定登机口'}】`
  }
  if (cap === 'CAP_BAGGAGE_MEASURE') {
    return `采集【${params.baggageLocation || '值机区'}】行李尺寸与重量数据`
  }
  if (cap === 'CAP_OVERSIZE_ALERT') {
    return `上报超规行李告警并提示前往【${params.targetCounter || '超规行李专柜'}】`
  }
  return Object.entries(params).map(([k, v]) => `${k}: ${v}`).join('，')
}

export function formatReadableFeedback(out, reasonCode) {
  if (!out || !Object.keys(out).length) return translateReasonCode(reasonCode)
  if (out.arrivalLocation) {
    return `已顺利抵达【${out.arrivalLocation}】（${out.arrivalStatus === 'ARRIVED' ? '到达确认' : out.arrivalStatus || '完成'}）`
  }
  if (out.lengthCm || out.weightKg) {
    const sum = Number(out.lengthCm || 0) + Number(out.widthCm || 0) + Number(out.heightCm || 0)
    return `实测 ${out.lengthCm}×${out.widthCm}×${out.heightCm} cm（三边和 ${sum} cm）、重量 ${out.weightKg} kg → 判定：${out.isOversize ? '超规行李' : '正常行李'}`
  }
  if (out.channelResult === 'UNCOVERED') {
    return `渠道未覆盖：${translateReasonCode(out.reason || reasonCode)}`
  }
  if (out.publishStatus === 'SUCCESS') return '航延屏已成功更新发布内容'
  if (out.displayStatus === 'SUCCESS') return '智慧航显已正常点亮展示'
  if (out.notificationStatus === 'SUCCESS') return '现场通知已播报送达'
  return translateReasonCode(reasonCode)
}
