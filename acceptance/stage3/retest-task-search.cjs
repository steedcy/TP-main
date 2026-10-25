// TC-063.S1/S3: live API filters, goal keyword, missing detail, and role gate.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const accounts = Object.fromEntries(fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .filter(line => /^\|(?:运行操作员|配置管理员)\|/.test(line))
  .map(line => { const [, role, username, password] = line.split('|'); return [role, { username, password }] }))
const origin = 'http://127.0.0.1:5173'
const api = 'http://127.0.0.1:8080/api/v1'
async function session(role) {
  const response = await fetch(api + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(accounts[role]) })
  return (await response.json()).data.token
}
async function get(route, token) {
  const response = await fetch(api + route, { headers: { Authorization: 'Bearer ' + token } })
  return { status: response.status, data: await response.json() }
}
async function main() {
  const operator = await session('运行操作员')
  const config = await session('配置管理员')
  const target = (await get('/tasks/19', operator)).data.data
  const code = target.taskCode
  const unique = 'P-R08-OVERSIZE'
  const exact = await get('/tasks?taskCode=' + encodeURIComponent(code), operator)
  const status = await get('/tasks?status=COMPLETED&page=1&size=100', operator)
  const family = await get('/tasks?taskFamily=OVERSIZE_BAGGAGE_HANDLING&page=1&size=100', operator)
  const keyword = await get('/tasks?keyword=' + encodeURIComponent(unique) + '&page=1&size=100', operator)
  const noResult = await get('/tasks/999999999', operator)
  const forbidden = await get('/tasks/19', config)
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', targetId: 19, taskCode: code,
    filters: { exactCodeTotal: exact.data.data?.totalElements,
      completedAllMatch: status.data.data?.content.every(row => row.status === 'COMPLETED'),
      familyAllMatch: family.data.data?.content.every(row => row.taskFamily === 'OVERSIZE_BAGGAGE_HANDLING'),
      keywordTotal: keyword.data.data?.totalElements,
      keywordMatchingRows: keyword.data.data?.content.filter(row => row.taskGoal.includes(unique)).length },
    missingApiHttpStatus: noResult.status, forbiddenApiHttpStatus: forbidden.status }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto(origin + '/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(accounts['运行操作员'].username)
    await page.locator('input[placeholder="密码"]').fill(accounts['运行操作员'].password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview', { timeout: 8000 })
    await page.goto(origin + '/tasks', { waitUntil: 'networkidle' })
    evidence.browser = { goalKeywordFieldCount: await page.locator('input[placeholder*="目标关键字"]').count(),
      taskCodeFieldCount: await page.locator('input[placeholder="任务编号"]').count(),
      defaultTimeRangeVisible: await page.locator('.ant-picker-range input').first().inputValue() }
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-063-S1-task-list.png') })
    await page.goto(origin + '/tasks/999999999', { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)
    evidence.browser.missingRoutePath = new URL(page.url()).pathname
    evidence.browser.returnedToList = new URL(page.url()).pathname === '/tasks'
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-063-S3-missing.png') })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-063-task-search.json'), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify(evidence) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
