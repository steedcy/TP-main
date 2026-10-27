// TC-054.S2: inspect completion progress and current step in the live task views.
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
  const ev = { observedAt, runtimeInput: 'V1.5', browser: 'Chrome', taskId: 19 }
  try {
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/tasks', { waitUntil: 'networkidle' })
    ev.listHeaders = await page.locator('thead th').allInnerTexts()
    ev.listProgressColumn = ev.listHeaders.some(x => x.includes('进度') || x.includes('当前步'))
    ev.listScreenshot = `TC-054-progress-list-${stamp}.png`
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.listScreenshot) })
    await page.goto('http://127.0.0.1:5173/tasks/19', { waitUntil: 'networkidle' })
    ev.detailHeader = await page.locator('.ant-descriptions').first().innerText()
    ev.detailText = await page.locator('body').innerText()
    ev.detailCardTitles = await page.locator('.ant-card-head-title').allInnerTexts()
    ev.assignmentRows = await page.locator('.ant-card').filter({ has: page.getByText('步骤设备分配与执行情况', { exact: true }) })
      .locator('tbody tr').allInnerTexts()
    ev.detailProgressLabel = /完成数\s*\/\s*总数|当前步|进度\s*[:：]?\s*\d+\s*\/\s*\d+/.test(ev.detailText)
    ev.detailScreenshot = `TC-054-progress-detail-${stamp}.png`
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.detailScreenshot), fullPage: true })
  } finally {
    await browser.close()
  }
  const name = `TC-054-progress-ui-${stamp}.json`
  fs.writeFileSync(path.join(__dirname, 'evidence', name), JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ evidence: name, status: ev.detailHeader.split('\n')[0],
    assignmentCount: ev.assignmentRows.length, listProgressColumn: ev.listProgressColumn,
    detailProgressLabel: ev.detailProgressLabel }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
