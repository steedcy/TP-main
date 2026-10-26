// TC-014.S2: capture the live offline marker, agent row, and detail dialog.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
const phase = process.argv[2]
if (!['offline', 'recovered'].includes(phase)) throw new Error('phase required')

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
    ev.situationMarkerClass = await marker.getAttribute('class')
    ev.situationMarkerTitle = await marker.getAttribute('title')
    const situationRow = page.locator('.ant-table-row').filter({ hasText: 'SIM_F2_DISPLAY' }).first()
    ev.situationRow = await situationRow.innerText()
    ev.situationLastReportedCell = await situationRow.locator('td').last().evaluate(el => ({
      text: el.textContent.trim(), className: el.className, html: el.innerHTML }))
    try {
      await marker.click({ timeout: 1500 })
      ev.markerClick = 'direct'
    } catch (error) {
      ev.markerClick = 'blocked-by-overlap'
      ev.markerClickError = String(error).slice(-700)
      // Inspect dialog content after recording the real pointer obstruction.
      await marker.evaluate(el => el.click())
    }
    const dialog = page.locator('.ant-modal-content').filter({ hasText: 'SIM_F2_DISPLAY' }).first()
    await dialog.waitFor({ state: 'visible' })
    ev.situationDetail = await dialog.innerText()
    ev.situationAlerts = await page.locator('.ant-alert').allInnerTexts()
    await page.screenshot({ path: path.join(__dirname, 'evidence', `TC-014-${phase}-situation.png`), fullPage: true })

    await page.goto('http://127.0.0.1:5173/device-agents', { waitUntil: 'networkidle' })
    const agentRow = page.locator('.ant-table-row').filter({ hasText: 'SIM_F2_DISPLAY' }).first()
    await agentRow.waitFor({ state: 'visible' })
    ev.agentRow = await agentRow.innerText()
    ev.agentLastReportedCell = await agentRow.locator('td').nth(7).evaluate(el => ({
      text: el.textContent.trim(), className: el.className, html: el.innerHTML }))
    ev.agentAlerts = await page.locator('.ant-alert').allInnerTexts()
    await page.screenshot({ path: path.join(__dirname, 'evidence', `TC-014-${phase}-agent.png`), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', `TC-014-${phase}-ui.json`),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ phase: ev.phase, markerClass: ev.situationMarkerClass,
    markerTitle: ev.situationMarkerTitle, agentRow: ev.agentRow }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
