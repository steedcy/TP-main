// SRS_F027.R07: inspect the V1.5 trace surface for out-of-scope export/report actions.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')

async function main() {
  const browser = await chromium.launch({ executablePath:
    'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome' }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/task-trace', { waitUntil: 'networkidle' })
    ev.route = new URL(page.url()).pathname
    ev.menuLinks = await page.locator('a[href]').evaluateAll(nodes => nodes.map(node => ({
      text: node.innerText.trim(), href: node.getAttribute('href')
    })).filter(row => row.text))
    ev.buttonsBefore = await page.getByRole('button').allInnerTexts()
    const search = page.locator('input[placeholder="任务编号（精确）"]')
    await search.fill('TASK-20261025-0019')
    await search.press('Enter')
    const row = page.locator('.ant-list-item').filter({ hasText: 'TASK-20261025-0019' })
    await row.waitFor({ state: 'visible' })
    await row.click()
    await page.locator('.ant-timeline-item').first().waitFor({ state: 'visible' })
    ev.buttonsAfter = await page.getByRole('button').allInnerTexts()
    ev.anchorTextsAfter = await page.locator('a[href]').allInnerTexts()
    ev.exportOrReportControls = await page.getByRole('button', { name: /导出|研究记录|评测报告|生成报告/ }).count()
    ev.traceEventCount = await page.locator('.ant-timeline-item').count()
    ev.screenshot = 'SRS_F027-R07-no-export-task19.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'SRS_F027-R07-no-export-task19.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ route: ev.route, traceEventCount: ev.traceEventCount,
    exportOrReportControls: ev.exportOrReportControls,
    buttonsBefore: ev.buttonsBefore, buttonsAfter: ev.buttonsAfter }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
