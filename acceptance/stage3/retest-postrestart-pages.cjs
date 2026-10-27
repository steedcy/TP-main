// TC-094.S2: view the live overview and newly completed task after manual restart.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const id = Number(process.argv[2])
if (!Number.isInteger(id) || id <= 0) throw Error('task id required')

async function main() {
  const browser = await chromium.launch({ executablePath:
    'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', taskId: id, requests: [], pages: {} }
  page.on('response', response => {
    if (response.url().includes('/api/v1/dashboard/overview') ||
        response.url().includes(`/api/v1/tasks/${id}`)) {
      evidence.requests.push({ url: response.url(), status: response.status() })
    }
  })
  try {
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    evidence.pages.overview = { route: new URL(page.url()).pathname,
      taskMetricVisible: await page.getByText('任务状态分布').isVisible() }
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-094-postrestart-overview.png') })
    await page.goto(`http://127.0.0.1:5173/tasks/${id}`, { waitUntil: 'networkidle' })
    evidence.pages.task = { route: new URL(page.url()).pathname,
      header: await page.locator('.ant-descriptions').first().innerText(),
      timelineItemCount: await page.locator('.ant-timeline-item').count() }
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-094-postrestart-task.png'), fullPage: true })
  } finally {
    fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-094-postrestart-pages.json'),
      JSON.stringify(evidence, null, 2) + '\n')
    await browser.close()
  }
  console.log(JSON.stringify({ pages: evidence.pages,
    apiResponses: evidence.requests.map(r => r.status) }))
}
main().catch(error => { console.error(String(error)); process.exitCode = 1 })
