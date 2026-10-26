// TC-014.S1: capture the situation marker and table after a signed status report.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
const phase = process.argv[2]
if (!/^[AB]$/.test(phase || '')) throw new Error('Phase A or B required')

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', phase, deviceCode: 'SIM_F2_DISPLAY' }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/situation', { waitUntil: 'networkidle' })
    const marker = page.locator('.device-marker').filter({ hasText: '智慧显示终端仿真体' }).first()
    await marker.waitFor({ state: 'visible' })
    ev.markerClass = await marker.getAttribute('class')
    ev.markerTitle = await marker.getAttribute('title')
    const row = page.locator('.ant-table-row').filter({ hasText: 'SIM_F2_DISPLAY' }).first()
    ev.tableRow = await row.innerText()
    ev.screenshot = `TC-014-status-${phase}.png`
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', `TC-014-status-${phase}-ui.json`),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ phase: ev.phase, markerClass: ev.markerClass,
    markerTitle: ev.markerTitle, tableRow: ev.tableRow }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
