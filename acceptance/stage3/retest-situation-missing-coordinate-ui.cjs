// TC-071.S1: inspect UI fallback against a browser-injected null-location snapshot.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const code = 'SIM_F2_DISPLAY'

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', role: '运行操作员', injectedCode: code, injection: 'snapshot location x/y null' }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.route('**/api/v1/situation/snapshot', async route => {
      const response = await route.fetch()
      const body = await response.json()
      const item = body.data.agents.find(a => a.deviceCode === code)
      ev.originalLocation = item.location
      item.location = { ...item.location, x: null, y: null }
      ev.injectedLocation = item.location
      await route.fulfill({ response, body: JSON.stringify(body) })
    })
    await page.goto('http://127.0.0.1:5173/situation', { waitUntil: 'networkidle' })
    await page.locator('.ant-alert-info').waitFor({ state: 'visible' })
    ev.alert = await page.locator('.ant-alert-info').innerText()
    ev.markerCount = await page.locator('.device-marker').count()
    ev.injectedMarkerCount = await page.locator('.device-marker').filter({ hasText: '智慧显示终端仿真体' }).count()
    const row = page.locator('.device-card tbody tr').filter({ hasText: code }).first()
    ev.injectedTableRow = await row.innerText()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-071-missing-coordinate-ui.png'), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-071-missing-coordinate-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ alert: ev.alert, markerCount: ev.markerCount,
    injectedMarkerCount: ev.injectedMarkerCount, injectedTableRow: ev.injectedTableRow }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
