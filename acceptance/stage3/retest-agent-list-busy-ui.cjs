// TC-011.S2: inspect a real busy agent and follow its current-task link.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
const agentId = process.argv[2]
const taskId = Number(process.argv[3])
if (!/^AGT-[A-Z0-9]{8}$/.test(agentId || '') || !Number.isInteger(taskId))
  throw new Error('Agent and task identifiers required')

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', agentId, taskId }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/device-agents', { waitUntil: 'networkidle' })
    const row = page.locator('.ant-table-row').filter({ hasText: agentId })
    await row.waitFor({ state: 'visible' })
    ev.route = new URL(page.url()).pathname
    ev.headers = await page.locator('.ant-table-thead th').allInnerTexts()
    ev.rowText = await row.innerText()
    ev.agentDetailLinkCount = await row.locator('a[href*="device-agents"]').count()
    ev.capabilitySummaryVisible = /CAP_|能力/.test(ev.rowText)
    const link = row.locator('a[href*="/tasks/"]')
    ev.currentTaskLinkCount = await link.count()
    ev.currentTaskHref = ev.currentTaskLinkCount ? await link.first().getAttribute('href') : null
    ev.listScreenshot = 'TC-011-busy-agent-list.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.listScreenshot), fullPage: true })
    if (ev.currentTaskLinkCount) {
      await link.first().click()
      await page.waitForURL('**/overview', { timeout: 3000 }).catch(() => {})
      await page.waitForLoadState('networkidle')
      ev.routeAfterTaskClick = new URL(page.url()).pathname
      ev.taskBodyExcerpt = (await page.locator('body').innerText()).slice(0, 600)
      ev.taskScreenshot = 'TC-011-busy-agent-task.png'
      await page.screenshot({ path: path.join(__dirname, 'evidence', ev.taskScreenshot), fullPage: true })
    }
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-011-busy-agent-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ route: ev.route, headers: ev.headers,
    currentTaskLinkCount: ev.currentTaskLinkCount, currentTaskHref: ev.currentTaskHref,
    routeAfterTaskClick: ev.routeAfterTaskClick, agentDetailLinkCount: ev.agentDetailLinkCount }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
