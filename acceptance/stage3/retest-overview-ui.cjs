// TC-004.S3 live period switch, refresh, and role display.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const rows = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .filter(line => /^\|(?:系统管理员|运行操作员|配置管理员)\|/.test(line))
const accounts = rows.map(line => { const [, role, username, password] = line.split('|'); return { role, username, password } })
async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome',
    viewport: '1366x768', roles: [] }
  try {
    for (const account of accounts) {
      const context = await browser.newContext({ viewport: { width: 1366, height: 768 } })
      const page = await context.newPage()
      const requests = []
      page.on('request', req => { if (req.url().includes('/api/v1/dashboard/overview')) requests.push(req.url()) })
      await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
      await page.locator('input[placeholder="账号"]').fill(account.username)
      await page.locator('input[placeholder="密码"]').fill(account.password)
      await page.locator('button[type="submit"]').click()
      await page.waitForURL('**/overview', { timeout: 10000 })
      await page.getByText('设备代理总数').waitFor({ state: 'visible', timeout: 8000 })
      const initial = requests.slice()
      const select = page.locator('.ant-select').first()
      const defaultToday = (await select.innerText()).includes('今日')
      await select.click()
      await Promise.all([page.waitForResponse(res => res.url().includes('/api/v1/dashboard/overview?period=LAST_7_DAYS')),
        page.getByText('近7日', { exact: true }).last().click()])
      if (!page.url().includes('/overview')) throw Error('left overview after period selection: ' + page.url())
      const refresh = page.locator('button').filter({ hasText: /刷\s*新/ })
      if (!(await refresh.count())) {
        throw Error('refresh button absent; buttons=' + JSON.stringify(await page.locator('button').allInnerTexts()))
      }
      await Promise.all([page.waitForResponse(res => res.url().includes('/api/v1/dashboard/overview?period=LAST_7_DAYS')),
        refresh.click()])
      const visibleTaskMetric = await page.getByText('任务状态分布').isVisible()
      const row = { role: account.role, defaultToday,
        initialTodayRequest: initial.some(url => url.includes('period=TODAY')),
        weekRequests: requests.filter(url => url.includes('period=LAST_7_DAYS')).length,
        taskMetricVisible: visibleTaskMetric,
        roleScopeExpected: visibleTaskMetric === (account.role !== '配置管理员'),
        refreshedAtVisible: await page.getByText(/更新于/).isVisible() }
      evidence.roles.push(row)
      await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-004-S3-' + account.username + '.png') })
      await context.close()
    }
  } finally { await browser.close() }
  evidence.pass = evidence.roles.length === 3 && evidence.roles.every(row =>
    row.defaultToday && row.initialTodayRequest && row.weekRequests >= 2 && row.roleScopeExpected && row.refreshedAtVisible)
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-004-overview-ui.json'), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ pass: evidence.pass, roles: evidence.roles }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
