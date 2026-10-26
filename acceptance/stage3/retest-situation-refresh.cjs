// TC-070.S2: operator view, live refresh cadence, busy task link and restored idle state.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const phase = process.argv[2]
const taskId = Number(process.argv[3])
if (!['busy', 'idle'].includes(phase) || (phase === 'busy' && !Number.isInteger(taskId)))
  throw new Error('phase and task id required')

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', role: '运行操作员', phase, taskId: phase === 'busy' ? taskId : null,
    snapshotResponses: [] }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    page.on('response', response => {
      if (response.url().endsWith('/api/v1/situation/snapshot')) {
        ev.snapshotResponses.push({ observedAt: new Date().toISOString(), httpStatus: response.status() })
      }
    })
    await page.goto('http://127.0.0.1:5173/situation', { waitUntil: 'networkidle' })
    const marker = page.locator('.device-marker').filter({ hasText: '智慧显示终端仿真体' }).first()
    await marker.waitFor({ state: 'visible' })
    ev.initialMarkerClass = await marker.getAttribute('class')
    ev.initialMarkerTitle = await marker.getAttribute('title')
    ev.refreshBadge = await page.locator('.page-header').innerText()
    ev.generatedAtStart = await page.locator('.updated-at').innerText()
    if (phase === 'busy') {
      await page.waitForTimeout(11700)
      ev.generatedAtAfterWait = await page.locator('.updated-at').innerText()
      ev.markerClassAfterWait = await marker.getAttribute('class')
    }
    // The default map has an overlapping robot marker. Filter to the display
    // type, then use a real pointer click to open its detail.
    const filters = page.locator('.type-filter input[type="checkbox"]')
    for (let i = 0; i < await filters.count(); i++) {
      if ((await filters.nth(i).getAttribute('value')) !== 'SMART_DISPLAY') {
        await filters.nth(i).evaluate(el => el.closest('label').click())
      }
    }
    ev.singleTypeChecked = await page.locator('.type-filter input[type="checkbox"]:checked').count()
    await marker.click({ timeout: 6000 })
    const dialog = page.locator('.ant-modal-content').filter({ hasText: 'SIM_F2_DISPLAY' }).first()
    await dialog.waitFor({ state: 'visible' })
    ev.detail = await dialog.innerText()
    ev.detailTaskLinkCount = await dialog.locator('a[href*="/tasks/"]').count()
    ev.detailTaskHref = ev.detailTaskLinkCount
      ? await dialog.locator('a[href*="/tasks/"]').first().getAttribute('href') : null
    await page.screenshot({ path: path.join(__dirname, 'evidence', `TC-070-situation-${phase}.png`), fullPage: true })
    if (phase === 'busy' && ev.detailTaskLinkCount) {
      await dialog.locator('a[href*="/tasks/"]').first().click()
      await page.waitForURL(`**/tasks/${taskId}`, { timeout: 10000 })
      ev.routeAfterClick = new URL(page.url()).pathname
      ev.taskPageExcerpt = (await page.locator('body').innerText()).slice(0, 900)
      await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-070-situation-task.png'), fullPage: true })
    }
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', `TC-070-situation-${phase}.json`),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ phase: ev.phase, responses: ev.snapshotResponses.length,
    initialClass: ev.initialMarkerClass, afterClass: ev.markerClassAfterWait,
    detailTaskHref: ev.detailTaskHref, routeAfterClick: ev.routeAfterClick }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
