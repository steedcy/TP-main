// TC-054.S1: verify the real two-step task's rows and timestamped timeline.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const account = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(line => line.startsWith('|运行操作员|'))
const [, , username, password] = account.split('|')

async function main() {
  const browser = await chromium.launch({ executablePath:
    'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const observedAt = new Date().toISOString()
  const stamp = observedAt.replace(/[-:.]/g, '').replace(/\d{3}Z$/, 'Z')
  const ev = { observedAt, runtimeInput: 'V1.5', browser: 'Chrome', taskId: 85 }
  try {
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/tasks/85', { waitUntil: 'networkidle' })
    ev.header = await page.locator('.ant-descriptions').first().innerText()
    const card = page.locator('.ant-card').filter({ has: page.getByText('步骤设备分配与执行情况', { exact: true }) })
    ev.stepHeaders = await card.locator('thead th').allInnerTexts()
    ev.stepRows = await card.locator('tbody tr').allInnerTexts()
    ev.timeline = await page.locator('.ant-timeline-item').allInnerTexts()
    ev.screenshot = `TC-054-two-step-order-ui-${stamp}.png`
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally {
    await browser.close()
  }
  const name = `TC-054-two-step-order-ui-${stamp}.json`
  fs.writeFileSync(path.join(__dirname, 'evidence', name), JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ evidence: name, stepCount: ev.stepRows.length,
    timelineCount: ev.timeline.length, status: ev.header.split('\n')[0] }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
