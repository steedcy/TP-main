// TC-023.S2: inspect the live agent list and whether a message-event detail route exists.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const agentId = 'AGT-0158A712'

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    role: '运行操作员', browser: 'Chrome', agentId }
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
    ev.listPath = new URL(page.url()).pathname
    ev.headers = await page.locator('.ant-table-thead th').allInnerTexts()
    ev.row = await row.innerText()
    ev.agentDetailLinks = await row.locator('a[href*="device-agents/"]').count()
    ev.eventTimelineEntries = await page.locator('.ant-timeline-item').count()
    ev.detailButtons = await row.getByRole('button', { name: /详情|事件/ }).count()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-023-agent-list.png'), fullPage: true })
    await page.goto(`http://127.0.0.1:5173/device-agents/${agentId}`, { waitUntil: 'networkidle' })
    ev.directDetailPath = new URL(page.url()).pathname
    ev.directBodyExcerpt = (await page.locator('body').innerText()).slice(0, 500)
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-023-agent-detail-route.png'), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-023-agent-event-detail-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ headers: ev.headers, agentDetailLinks: ev.agentDetailLinks,
    eventTimelineEntries: ev.eventTimelineEntries, detailButtons: ev.detailButtons,
    directDetailPath: ev.directDetailPath }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
