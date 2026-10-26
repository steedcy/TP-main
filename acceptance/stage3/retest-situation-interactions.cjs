// TC-070.S1/S3: live Chrome map interactions, coordinates and presentation scope.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', viewport: '1366x768', mutationsAfterOpen: [] }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    page.on('request', req => {
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method())) {
        ev.mutationsAfterOpen.push({ method: req.method(), path: new URL(req.url()).pathname })
      }
    })
    const responsePromise = page.waitForResponse(res => res.url().endsWith('/api/v1/situation/snapshot') && res.status() === 200)
    await page.goto('http://127.0.0.1:5173/situation', { waitUntil: 'networkidle' })
    ev.snapshot = (await (await responsePromise).json()).data
    await page.locator('.device-marker').first().waitFor({ state: 'visible' })
    ev.defaultChecked = await page.locator('.type-filter input[type="checkbox"]:checked').count()
    ev.typeOptions = await page.locator('.type-filter label').allInnerTexts()
    ev.legend = await page.locator('.map-legend').innerText()
    ev.initialMarkerCount = await page.locator('.device-marker').count()
    ev.initialRows = await page.locator('.device-card .ant-table-row').count()
    ev.floorplan = await page.locator('.floorplan').evaluate(img => ({
      loaded: img.complete && img.naturalWidth > 0, naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight, displayedWidth: img.clientWidth,
      displayedHeight: img.clientHeight }))
    ev.canvasStyleInitial = await page.locator('.map-canvas').getAttribute('style')
    ev.markers = await page.locator('.device-marker').evaluateAll(items => items.map(el => ({
      name: el.textContent.trim(), title: el.title, className: el.className,
      left: el.style.left, top: el.style.top })))
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-070-map-default.png'), fullPage: true })

    await page.getByRole('button', { name: '放大底图' }).click()
    ev.zoomAfterIn = await page.locator('.zoom-label').innerText()
    ev.canvasStyleZoomed = await page.locator('.map-canvas').getAttribute('style')
    await page.getByRole('button', { name: '缩小底图' }).click()
    ev.zoomAfterOut = await page.locator('.zoom-label').innerText()
    await page.getByRole('button', { name: '查看全图' }).click()
    ev.zoomFitAll = await page.locator('.zoom-label').innerText()
    await page.getByRole('button', { name: '适应宽度' }).click()
    ev.zoomFitWidth = await page.locator('.zoom-label').innerText()
    const box = await page.locator('.map-viewport').boundingBox()
    await page.mouse.move(box.x + 45, box.y + 55)
    await page.mouse.down()
    await page.mouse.move(box.x + 105, box.y + 85, { steps: 4 })
    await page.mouse.up()
    ev.canvasStylePanned = await page.locator('.map-canvas').getAttribute('style')

    const filters = page.locator('.type-filter input[type="checkbox"]')
    ev.filterValues = await filters.evaluateAll(items => items.map(el => el.value))
    for (let i = 0; i < await filters.count(); i++) {
      if ((await filters.nth(i).getAttribute('value')) !== 'SMART_DISPLAY') {
        await filters.nth(i).evaluate(el => el.closest('label').click())
      }
    }
    ev.singleTypeChecked = await page.locator('.type-filter input[type="checkbox"]:checked').count()
    ev.singleTypeMarkers = await page.locator('.device-marker').allInnerTexts()
    ev.singleTypeRows = await page.locator('.device-card .ant-table-row').allInnerTexts()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-070-map-filtered.png'), fullPage: true })
    for (let i = 0; i < await filters.count(); i++) {
      if (!(await filters.nth(i).isChecked())) await filters.nth(i).evaluate(el => el.closest('label').click())
    }
    ev.restoredMarkerCount = await page.locator('.device-marker').count()
    const display = page.locator('.device-marker').filter({ hasText: '智慧显示终端仿真体' }).first()
    try {
      await display.click({ timeout: 1500 })
      ev.displayClick = 'direct'
    } catch (error) {
      ev.displayClick = 'blocked-by-overlap'
      ev.displayClickError = String(error).slice(-700)
    }
    const baggage = page.locator('.device-marker').filter({ hasText: '行李测量仪仿真体' }).first()
    await baggage.evaluate(el => el.click())
    const dialog = page.locator('.ant-modal-content').filter({ hasText: 'SIM_F2_BAGGAGE' }).first()
    await dialog.waitFor({ state: 'visible' })
    ev.selectedBaggageDetail = await dialog.innerText()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-070-map-selected.png'), fullPage: true })
    ev.scopeButtons = await page.locator('.situation-page button').allInnerTexts()
    ev.scopeHint = await page.locator('.map-hint').innerText()
    ev.noOperationLabels = {
      deviceCommand: await page.getByText(/下发指令|执行指令/).count(),
      onlineEdit: await page.getByText(/在线编辑|编辑设备/).count(),
      mapVersion: await page.getByText(/地图版本|底图版本/).count(),
      trajectoryReplay: await page.getByText(/轨迹回放/).count()
    }
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-070-situation-interactions.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ checked: ev.defaultChecked, markers: ev.initialMarkerCount,
    filtered: ev.singleTypeMarkers?.length, displayClick: ev.displayClick,
    zoom: [ev.zoomAfterIn, ev.zoomAfterOut, ev.zoomFitAll, ev.zoomFitWidth] }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
