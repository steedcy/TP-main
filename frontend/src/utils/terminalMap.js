export const MAP_WIDTH = 1260
export const MAP_HEIGHT = 6895

export const POI_CATEGORIES = [
  { key: 'GATE', label: '登机口', color: '#1677ff', badge: 'G' },
  { key: 'CHECKIN', label: '值机柜台', color: '#13c2c2', badge: 'C' },
  { key: 'BAGGAGE', label: '行李托运/专柜', color: '#fa8c16', badge: 'B' },
  { key: 'SECURITY', label: '安检通道', color: '#722ed1', badge: 'S' },
  { key: 'MEASURE', label: '行李测量点', color: '#eb2f96', badge: 'M' },
  { key: 'SERVICE', label: '服务枢纽', color: '#52c41a', badge: 'H' }
]

export const TERMINAL_POIS = [
  // 值机柜台
  { code: 'T2值机岛A01', name: 'T2值机岛 A01', category: 'CHECKIN', x: 400, y: 3100, zone: 'T2值机区-北' },
  { code: 'T2值机岛A02', name: 'T2值机岛 A02', category: 'CHECKIN', x: 400, y: 3250, zone: 'T2值机区-北' },
  { code: 'T2值机岛B01', name: 'T2值机岛 B01', category: 'CHECKIN', x: 465, y: 3447, zone: 'T2值机区-中' },
  { code: 'T2值机岛A03', name: 'T2值机岛 A03', category: 'CHECKIN', x: 805, y: 4050, zone: 'T2值机区-南' },
  { code: 'T2值机区', name: 'T2值机区（会合点）', category: 'CHECKIN', x: 805, y: 4050, zone: 'T2值机区-南', aliases: ['F2_BAGGAGE_POINT'] },

  // 行李托运与超规专柜
  { code: '行李托运柜台A01', name: '行李托运柜台 A01', category: 'BAGGAGE', x: 430, y: 3180, zone: '行李托运区' },
  { code: '行李托运柜台B02', name: '行李托运柜台 B02', category: 'BAGGAGE', x: 490, y: 3520, zone: '行李托运区' },
  { code: '超规行李专柜B01', name: '超规行李专柜 B01', category: 'BAGGAGE', x: 810, y: 4200, zone: '超规行李专柜区', aliases: ['F2_SERVICE_POINT'] },

  // 智能行李测量点
  { code: '智能行李测量点A', name: '智能行李测量点 A（主）', category: 'MEASURE', x: 400, y: 3106, zone: 'T2值机区-北' },
  { code: '智能行李测量点B', name: '智能行李测量点 B（备）', category: 'MEASURE', x: 465, y: 3447, zone: 'T2值机区-中' },

  // 安检通道
  { code: '安检通道01', name: '安检通道 01（普通）', category: 'SECURITY', x: 630, y: 3750, zone: '中央安检区' },
  { code: '安检通道02', name: '安检通道 02（普通）', category: 'SECURITY', x: 740, y: 3750, zone: '中央安检区' },
  { code: 'VIP安检通道', name: 'VIP / 特殊旅客安检通道', category: 'SECURITY', x: 840, y: 3750, zone: '中央安检区' },

  // 服务枢纽
  { code: '航显中心点', name: '智慧航显信息中心', category: 'SERVICE', x: 870, y: 2960, zone: 'F2中庭北区' },
  { code: '旅客服务中心', name: '旅客综合服务中心', category: 'SERVICE', x: 630, y: 4150, zone: 'F2中庭南区' },

  // 登机口
  { code: 'GATE_A01', name: '登机口 A01', category: 'GATE', x: 500, y: 4600, zone: 'A指廊' },
  { code: 'GATE_A02', name: '登机口 A02', category: 'GATE', x: 610, y: 4600, zone: 'A指廊' },
  { code: 'GATE_A03', name: '登机口 A03', category: 'GATE', x: 710, y: 4600, zone: 'A指廊' },
  { code: 'GATE_A05', name: '登机口 A05', category: 'GATE', x: 815, y: 4600, zone: 'A指廊', aliases: ['F2_TEST_GATE'] },
  { code: 'GATE_A06', name: '登机口 A06', category: 'GATE', x: 920, y: 4600, zone: 'A指廊' },
  { code: 'GATE_B01', name: '登机口 B01', category: 'GATE', x: 420, y: 5200, zone: 'B指廊' },
  { code: 'GATE_B02', name: '登机口 B02', category: 'GATE', x: 620, y: 5200, zone: 'B指廊' },
  { code: 'GATE_B03', name: '登机口 B03', category: 'GATE', x: 820, y: 5200, zone: 'B指廊' }
]

// 走廊路网节点与连通边，用于计算多段真实走廊引导路线
const CORRIDOR_NODES = [
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
  { id: 'N_GATE_A_FAR', x: 920, y: 4520 },
  { id: 'N_GATE_B_W', x: 420, y: 5120 },
  { id: 'N_GATE_B_M', x: 620, y: 5120 },
  { id: 'N_GATE_B_E', x: 820, y: 5120 }
]

const CORRIDOR_EDGES = [
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
  ['N_GATE_A_E', 'N_GATE_A_FAR'],
  ['N_GATE_A_W', 'N_GATE_B_W'],
  ['N_GATE_A_M', 'N_GATE_B_M'],
  ['N_GATE_A_E', 'N_GATE_B_E'],
  ['N_GATE_B_W', 'N_GATE_B_M'],
  ['N_GATE_B_M', 'N_GATE_B_E']
]

function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

export function resolveLocation(input, devices = []) {
  if (!input) return null
  if (typeof input === 'object' && Number.isFinite(Number(input.x)) && Number.isFinite(Number(input.y))) {
    return { x: Number(input.x), y: Number(input.y), label: input.label || '自定义位置' }
  }
  const text = String(input).trim()
  const exact = TERMINAL_POIS.find(p => p.code === text || p.name === text || (p.aliases && p.aliases.includes(text)))
  if (exact) return { x: exact.x, y: exact.y, label: exact.name, code: exact.code }

  const fuzzy = TERMINAL_POIS.find(p => text.includes(p.code) || p.code.includes(text))
  if (fuzzy) return { x: fuzzy.x, y: fuzzy.y, label: fuzzy.name, code: fuzzy.code }

  const dev = devices.find(d => d.deviceCode === text || d.deviceName === text)
  if (dev && dev.location && Number.isFinite(Number(dev.location.x)) && Number.isFinite(Number(dev.location.y))) {
    return { x: Number(dev.location.x), y: Number(dev.location.y), label: dev.deviceName || dev.deviceCode, code: dev.deviceCode }
  }
  return null
}

export function nearestPoi(x, y) {
  let best = null
  let bestDist = Infinity
  for (const poi of TERMINAL_POIS) {
    const d = Math.hypot(poi.x - x, poi.y - y)
    if (d < bestDist) {
      bestDist = d
      best = poi
    }
  }
  return best ? { ...best, distance: Math.round(bestDist) } : null
}

function dijkstraPath(startNodeId, endNodeId) {
  const nodeMap = Object.fromEntries(CORRIDOR_NODES.map(n => [n.id, n]))
  const adj = Object.fromEntries(CORRIDOR_NODES.map(n => [n.id, []]))
  for (const [u, v] of CORRIDOR_EDGES) {
    const w = dist(nodeMap[u], nodeMap[v])
    adj[u].push({ to: v, w })
    adj[v].push({ to: u, w })
  }
  const d = Object.fromEntries(CORRIDOR_NODES.map(n => [n.id, Infinity]))
  const prev = {}
  const visited = new Set()
  d[startNodeId] = 0

  while (visited.size < CORRIDOR_NODES.length) {
    let cur = null
    let curDist = Infinity
    for (const n of CORRIDOR_NODES) {
      if (!visited.has(n.id) && d[n.id] < curDist) {
        cur = n.id
        curDist = d[n.id]
      }
    }
    if (!cur || cur === endNodeId) break
    visited.add(cur)
    for (const edge of adj[cur]) {
      if (!visited.has(edge.to) && d[cur] + edge.w < d[edge.to]) {
        d[edge.to] = d[cur] + edge.w
        prev[edge.to] = cur
      }
    }
  }
  const chain = []
  let p = endNodeId
  while (p) {
    chain.unshift(nodeMap[p])
    p = prev[p]
  }
  return chain
}

function nearestCorridorNode(point) {
  let best = CORRIDOR_NODES[0]
  let bestD = Infinity
  for (const n of CORRIDOR_NODES) {
    const d = dist(n, point)
    if (d < bestD) {
      bestD = d
      best = n
    }
  }
  return best
}

export function computeTerminalRoute(stops) {
  const resolved = stops.filter(Boolean)
  if (resolved.length < 2) return { points: resolved, totalPixels: 0 }

  const points = []
  let totalPixels = 0
  for (let i = 0; i < resolved.length - 1; i++) {
    const a = resolved[i]
    const b = resolved[i + 1]
    const nStart = nearestCorridorNode(a)
    const nEnd = nearestCorridorNode(b)
    const corridor = dijkstraPath(nStart.id, nEnd.id)
    const segment = [a, ...corridor, b]
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
