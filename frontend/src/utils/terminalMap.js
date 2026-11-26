export const MAP_WIDTH = 2000
export const MAP_HEIGHT = 600

export const POI_CATEGORIES = [
  { key: 'GATE', label: '登机口', color: '#1677ff', badge: '登' },
  { key: 'CHECKIN', label: '值机柜台', color: '#13c2c2', badge: '值' },
  { key: 'BAGGAGE', label: '行李托运柜台', color: '#fa8c16', badge: '托' },
  { key: 'SECURITY', label: '安检通道', color: '#722ed1', badge: '安' },
  { key: 'MEASURE', label: '智能行李测量点', color: '#eb2f96', badge: '测' },
  { key: 'SERVICE', label: '服务柜台', color: '#52c41a', badge: '服' },
  { key: 'SHOP', label: '商铺餐饮', color: '#faad14', badge: '商' },
  { key: 'FACILITY', label: '公共设施（卫生间/母婴室/医疗室）', color: '#2f54eb', badge: '设' }
]

export function poiIcon(poi) {
  const name = String(poi?.poiName || '')
  if (name.includes('登机口')) return '✈️'
  if (name.includes('门') || name.includes('出入口')) return '🚪'
  if (name.includes('安全检查')) return '🛡️'
  if (name.includes('安全保卫')) return '👮'
  if (name.includes('洗手间')) return '🚻'
  if (name.includes('饮用水')) return '🚰'
  if (name.includes('餐饮')) return '🍽️'
  if (name.includes('商店')) return '🛍️'
  if (name.includes('母婴')) return '👶'
  if (name.includes('急救')) return '🏥'
  if (name.includes('电梯')) return '🛗'
  if (name.includes('扶梯') || name.includes('楼梯')) return '🪜'
  if (name.includes('行李开包')) return '🧳'
  if (name.includes('测量')) return '⚖️'
  if (name.includes('头等舱')) return '🛋️'
  if (name.includes('售票')) return '🎫'
  if (name.includes('服务台') || name.includes('问询') || name.includes('候机厅')) return 'ℹ️'
  return POI_CATEGORIES.find(c => c.key === poi?.category)?.badge || '📍'
}

export const DEFAULT_TERMINAL_POIS = [
  { poiCode: 'GATE_01', poiName: '1号登机口', category: 'GATE', x: 239, y: 56, zone: '候机区-西' },
  { poiCode: 'GATE_02', poiName: '2号登机口', category: 'GATE', x: 482, y: 57, zone: '候机区-西' },
  { poiCode: 'GATE_03', poiName: '3号登机口', category: 'GATE', x: 719, y: 56, zone: '候机区-西' },
  { poiCode: 'GATE_04', poiName: '4号登机口', category: 'GATE', x: 1022, y: 57, zone: '候机区-中' },
  { poiCode: 'GATE_05', poiName: '5号登机口', category: 'GATE', x: 1257, y: 56, zone: '候机区-东' },
  { poiCode: 'GATE_06', poiName: '6号登机口', category: 'GATE', x: 1685, y: 56, zone: '候机区-东' },
  { poiCode: 'SERVICE_DESK', poiName: '服务台', category: 'SERVICE', x: 1028, y: 135, zone: '候机区-中', linkedDeviceCode: 'SIM_DISPLAY_H2' },
  { poiCode: 'SECURITY_MAIN', poiName: '安全检查', category: 'SECURITY', x: 1037, y: 286, zone: '中央安检区' },
  { poiCode: 'CHECKIN_WEST', poiName: '售票', category: 'SERVICE', x: 896, y: 435, zone: '值机区-西' },
  { poiCode: 'CHECKIN_EAST', poiName: '问询', category: 'SERVICE', x: 1123, y: 435, zone: '值机区-东' },
  { poiCode: 'MEASURE_WEST', poiName: '智能行李测量点01', category: 'MEASURE', x: 520, y: 425, zone: '值机区-西', linkedDeviceCode: 'SIM_SCANNER_W' },
  { poiCode: 'MEASURE_EAST', poiName: '智能行李测量点02', category: 'MEASURE', x: 1420, y: 425, zone: '值机区-东', linkedDeviceCode: 'SIM_SCANNER_E' },
  { poiCode: 'PET_CHANNEL', poiName: '宠物托运专用通道', category: 'SERVICE', x: 260, y: 260, zone: '中间西区' },
  { poiCode: 'OVERSIZE_PACKING', poiName: '超规行李打包处', category: 'BAGGAGE', x: 180, y: 318, zone: '中间西区' },
  { poiCode: 'OVERSIZE_CHECKIN', poiName: '超规行李托运处', category: 'BAGGAGE', x: 310, y: 318, zone: '中间西区' },
  { poiCode: 'OVERSIZE_STORAGE', poiName: '超规行李寄存处', category: 'BAGGAGE', x: 450, y: 318, zone: '中间西区' },
  { poiCode: 'SPECIAL_SERVICE_DESK', poiName: '特殊旅客服务台', category: 'SERVICE', x: 1600, y: 318, zone: '中间东区' },
  { poiCode: 'REBOOK_COUNTER', poiName: '改签退票柜台', category: 'SERVICE', x: 1720, y: 318, zone: '中间东区' },
  { poiCode: 'TRANSFER_COUNTER', poiName: '中转柜台', category: 'SERVICE', x: 1830, y: 318, zone: '中间东区' },
  { poiCode: 'DUTY_MANAGER_DESK', poiName: '值班经理接待点', category: 'SERVICE', x: 1810, y: 260, zone: '中间东区' },
  { poiCode: 'MEAL_VOUCHER_POINT', poiName: '餐食发放登记处', category: 'SERVICE', x: 1905, y: 260, zone: '中间东区' },
  { poiCode: 'SHUTTLE_GATE', poiName: '远机位摆渡点', category: 'FACILITY', x: 1820, y: 115, zone: '候机区-东' },
  { poiCode: 'ENTRANCE_01', poiName: '1号门', category: 'FACILITY', x: 311, y: 520, zone: '值机区-南' },
  { poiCode: 'ENTRANCE_02', poiName: '2号门', category: 'FACILITY', x: 1036, y: 520, zone: '值机区-南' },
  { poiCode: 'ENTRANCE_03', poiName: '3号门', category: 'FACILITY', x: 1877, y: 520, zone: '值机区-南' }
]

const DEFAULT_CORRIDOR_NODES = [
  { id: 'N_H_G1', x: 239, y: 115 },
  { id: 'N_H_G2', x: 482, y: 115 },
  { id: 'N_H_G3', x: 719, y: 115 },
  { id: 'N_H_MID', x: 1028, y: 115 },
  { id: 'N_H_G5', x: 1257, y: 115 },
  { id: 'N_H_G6', x: 1685, y: 115 },
  { id: 'N_SEC_N', x: 1038, y: 235 },
  { id: 'N_SEC_M', x: 1038, y: 288 },
  { id: 'N_SEC_S', x: 1038, y: 341 },
  { id: 'N_C_W1', x: 311, y: 425 },
  { id: 'N_C_W2', x: 520, y: 425 },
  { id: 'N_C_MID', x: 1038, y: 425 },
  { id: 'N_C_E2', x: 1420, y: 425 },
  { id: 'N_C_E3', x: 1877, y: 425 },
  { id: 'N_ENT_2', x: 1036, y: 520 }
]

const DEFAULT_CORRIDOR_EDGES = [
  ['N_H_G1', 'N_H_G2'],
  ['N_H_G2', 'N_H_G3'],
  ['N_H_G3', 'N_H_MID'],
  ['N_H_MID', 'N_H_G5'],
  ['N_H_G5', 'N_H_G6'],
  ['N_H_MID', 'N_SEC_N'],
  ['N_SEC_N', 'N_SEC_M'],
  ['N_SEC_M', 'N_SEC_S'],
  ['N_SEC_S', 'N_C_MID'],
  ['N_C_W1', 'N_C_W2'],
  ['N_C_W2', 'N_C_MID'],
  ['N_C_MID', 'N_C_E2'],
  ['N_C_E2', 'N_C_E3'],
  ['N_C_MID', 'N_ENT_2']
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
  const aliases = {
    F2_SERVICE_POINT: 'SERVICE_DESK',
    F2_BAGGAGE_POINT: 'OVERSIZE_CHECKIN',
    F2_TEST_GATE: 'GATE_04',
    GATE_A05: 'GATE_05',
    '登机口13': 'GATE_01',
    'VIP值机柜台': 'CHECKIN_WEST',
    '国内值机柜台02': 'CHECKIN_WEST',
    '超规行李托运': 'OVERSIZE_CHECKIN',
    '宠物托运专用通道': 'PET_CHANNEL',
    '超规行李打包处': 'OVERSIZE_PACKING',
    '超规行李托运处': 'OVERSIZE_CHECKIN',
    '超规行李寄存处': 'OVERSIZE_STORAGE',
    '改签退票柜台': 'REBOOK_COUNTER',
    '特殊旅客服务台': 'SPECIAL_SERVICE_DESK',
    '中转柜台': 'TRANSFER_COUNTER',
    '行李提取与分拣区': 'BAGGAGE_CLAIM_W',
    '值班经理接待点': 'DUTY_MANAGER_DESK',
    '餐食发放登记处': 'MEAL_VOUCHER_POINT',
    '远机位摆渡点': 'SHUTTLE_GATE'
  }
  let normalized = aliases[text] || text
  const gateNumMatch = normalized.match(/(?:[A-Za-z]-?)?(\d{1,3})\s*号?登机口|^GATE[_-]?(\d{1,3})$|^[A-HJ-Z](\d{1,3})$/i)
  if (gateNumMatch) {
    const num = Number(gateNumMatch[1] || gateNumMatch[2] || gateNumMatch[3])
    normalized = `GATE_${String(((Math.max(1, num) - 1) % 6) + 1).padStart(2, '0')}`
  }
  const entNumMatch = normalized.match(/(\d{1,2})\s*号门|(\d{1,2})\s*号出入口|^ENTRANCE[_-]?(\d{1,2})$/i)
  if (entNumMatch) {
    const num = Number(entNumMatch[1] || entNumMatch[2] || entNumMatch[3])
    normalized = `ENTRANCE_${String(((Math.max(1, num) - 1) % 3) + 1).padStart(2, '0')}`
  }

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
  const blockedPolygons = regions
    .filter(r => r.regionType === 'SHOP_BLOCK' || r.regionType === 'WALL')
    .map(parseRegionGeometry)
    .filter(pts => pts.length >= 3)

  let nodes = []
  let edges = []

  if (customCorridors.length > 0) {
    let idx = 0
    for (const c of customCorridors) {
      const pts = parseRegionGeometry(c)
      const groupIds = []
      for (let i = 0; i < pts.length; i++) {
        const nid = `C_${idx++}`
        nodes.push({ id: nid, x: Number(pts[i].x), y: Number(pts[i].y) })
        groupIds.push(nid)
        if (i > 0) edges.push([groupIds[i - 1], nid])
      }
    }
    // 自动连接相邻走廊的接近节点（<= 120px），且不穿过商铺/墙体等不可通行区域
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (dist(nodes[i], nodes[j]) <= 120 && !segmentCrossesPolygons(nodes[i], nodes[j], blockedPolygons)) {
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
    SPECIAL_PASSENGER_SERVICE: '特殊旅客协同服务场景',
    GENERAL_SERVICE: '通用协同服务场景'
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
