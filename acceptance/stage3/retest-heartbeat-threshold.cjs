// TC-014.S3: live configuration UI inspection for heartbeat timeout control.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')

async function main() {
  const app = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const result = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome', viewport: '1366x768' }
  try {
    const page = await app.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    result.menuHeartbeatControlCount = await page.getByText(/心跳阈值|心跳超时/).count()
    await page.goto('http://127.0.0.1:5173/devices', { waitUntil: 'networkidle' })
    result.deviceListHeartbeatControlCount = await page.getByText(/心跳阈值|心跳超时/).count()
    await page.getByRole('button', { name: '新增设备' }).click()
    result.deviceFormHeartbeatControlCount = await page.locator('.ant-modal-content').getByText(/心跳阈值|心跳超时/).count()
    result.reportingIntervalControlCount = await page.locator('.ant-modal-content').getByText(/状态上报周期/).count()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-014-heartbeat-threshold-ui.png') })
  } finally { await app.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-014-heartbeat-threshold.json'), JSON.stringify(result, null, 2) + '\n')
  process.stdout.write(JSON.stringify(result) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
