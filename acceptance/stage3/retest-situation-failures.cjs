// TC-071.S2: browser fault injection for missing map asset and failed snapshot refresh.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const evidence = path.join(__dirname, 'evidence')

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', role: '运行操作员', injectedFaults: [], responses: [] }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    let failSnapshot = false
    page.on('response', response => {
      if (response.url().endsWith('/api/v1/situation/snapshot'))
        ev.responses.push({ at: new Date().toISOString(), status: response.status() })
    })
    await page.route('**/F2.jpg', route => {
      ev.injectedFaults.push({ at: new Date().toISOString(), target: 'F2.jpg', action: 'abort' })
      return route.abort('failed')
    })
    await page.route('**/api/v1/situation/snapshot', route => {
      if (!failSnapshot) return route.continue()
      ev.injectedFaults.push({ at: new Date().toISOString(), target: '/api/v1/situation/snapshot', action: '503' })
      return route.fulfill({ status: 503, contentType: 'application/json',
        body: JSON.stringify({ code: 503, message: 'test injected failure' }) })
    })
    await page.goto('http://127.0.0.1:5173/situation', { waitUntil: 'networkidle' })
    await page.locator('.map-error').waitFor({ state: 'visible' })
    ev.mapErrorText = await page.locator('.map-error').innerText()
    ev.mapImageNaturalWidth = await page.locator('img.floorplan').evaluate(el => el.naturalWidth)
    ev.markerCountBefore = await page.locator('.device-marker').count()
    ev.tableRowCountBefore = await page.locator('.device-card tbody tr').count()
    ev.tableTextBefore = await page.locator('.device-card').innerText()
    ev.generatedAtBefore = await page.locator('.updated-at').innerText()
    await page.screenshot({ path: path.join(evidence, 'TC-071-map-missing.png'), fullPage: true })
    failSnapshot = true
    await page.locator('.page-header button').click()
    await page.locator('.ant-alert-warning').waitFor({ state: 'visible' })
    ev.refreshWarning = await page.locator('.ant-alert-warning').innerText()
    ev.markerCountAfter = await page.locator('.device-marker').count()
    ev.tableRowCountAfter = await page.locator('.device-card tbody tr').count()
    ev.tableTextAfter = await page.locator('.device-card').innerText()
    ev.generatedAtAfter = await page.locator('.updated-at').innerText()
    await page.screenshot({ path: path.join(evidence, 'TC-071-refresh-failed.png'), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(evidence, 'TC-071-situation-failures.json'), JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ mapErrorText: ev.mapErrorText,
    refreshWarning: ev.refreshWarning, markerCounts: [ev.markerCountBefore, ev.markerCountAfter],
    tableRowCounts: [ev.tableRowCountBefore, ev.tableRowCountAfter],
    responses: ev.responses }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
