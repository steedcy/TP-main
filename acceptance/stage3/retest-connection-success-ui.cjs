// TC-009.S1: observe a fresh successful connection test in Chrome.
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
    browser: 'Chrome', deviceCode: 'SIM_F2_DISPLAY' }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/devices', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="按名称/编码检索"]').fill(ev.deviceCode)
    await page.locator('input[placeholder="按名称/编码检索"]').press('Enter')
    const row = page.locator('.ant-table-row').filter({ hasText: ev.deviceCode })
    await row.waitFor({ state: 'visible' })
    ev.beforeRow = await row.innerText()
    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/devices/' + ev.deviceCode + '/connection-test') &&
      response.request().method() === 'POST')
    await row.getByRole('button', { name: '连接测试' }).click()
    const response = await responsePromise
    ev.httpStatus = response.status()
    ev.responseBody = await response.json()
    await page.getByText('连接测试通过').waitFor({ state: 'visible' })
    ev.toastText = await page.locator('.ant-message-notice').last().innerText()
    ev.afterRow = await row.innerText()
    ev.durationInToast = /耗时|毫秒|ms|秒/.test(ev.toastText)
    ev.durationInResponse = /duration|elapsed|cost|耗时/i.test(JSON.stringify(ev.responseBody))
    ev.screenshot = 'TC-009-connection-success-ui.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-009-connection-success-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ httpStatus: ev.httpStatus, toastText: ev.toastText,
    durationInToast: ev.durationInToast, durationInResponse: ev.durationInResponse }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
