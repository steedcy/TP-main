// TC-010.S3: cancel and then confirm deletion of the same idle test device.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
const code = process.argv[2]
if (!/^S3_TC010_[A-Z0-9_]+$/.test(code || '')) throw new Error('Expected a stage-3 temporary device code')

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', deviceCode: code }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/devices', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="按名称/编码检索"]').fill(code)
    await page.locator('input[placeholder="按名称/编码检索"]').press('Enter')
    const row = page.locator('.ant-table-row').filter({ hasText: code })
    await row.waitFor({ state: 'visible' })
    ev.beforeRow = await row.innerText()
    let deleteRequests = 0
    page.on('request', request => {
      if (request.url().includes('/devices/' + code) && request.method() === 'DELETE') deleteRequests++
    })
    await row.locator('button').filter({ hasText: /删/ }).last().click()
    const confirm = page.locator('.ant-popconfirm').last()
    await confirm.waitFor({ state: 'visible' })
    ev.confirmationText = await confirm.innerText()
    ev.beforeScreenshot = 'TC-010-delete-before.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.beforeScreenshot), fullPage: true })
    await confirm.locator('.ant-popconfirm-buttons button').first().click()
    await page.waitForTimeout(400)
    ev.deleteRequestsAfterCancel = deleteRequests
    ev.presentAfterCancel = await row.isVisible()
    ev.afterCancelRow = ev.presentAfterCancel ? await row.innerText() : null
    ev.cancelScreenshot = 'TC-010-delete-cancel.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.cancelScreenshot), fullPage: true })
    await row.locator('button').filter({ hasText: /删/ }).last().click()
    await confirm.waitFor({ state: 'visible' })
    const deletion = page.waitForResponse(response =>
      response.url().includes('/devices/' + code) && response.request().method() === 'DELETE')
    await confirm.locator('.ant-popconfirm-buttons button').last().click()
    ev.deleteHttpStatus = (await deletion).status()
    ev.deleteRequestsAfterConfirm = deleteRequests
    await row.waitFor({ state: 'detached', timeout: 8000 })
    ev.presentAfterConfirm = await row.count() > 0
    ev.deleteToast = await page.locator('.ant-message-notice').last().innerText().catch(() => '')
    ev.afterScreenshot = 'TC-010-delete-confirmed.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.afterScreenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-010-device-delete-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ presentAfterCancel: ev.presentAfterCancel,
    deleteHttpStatus: ev.deleteHttpStatus, presentAfterConfirm: ev.presentAfterConfirm }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
