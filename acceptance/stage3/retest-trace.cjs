// TC-084: live trace filters, plan detail, event order, and empty results.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const browser = chromium
async function main() {
  const app = await browser.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome',
    viewport: '1366x768', taskId: 19, taskCode: 'TASK-20261025-0019' }
  try {
    const page = await app.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview', { timeout: 8000 })
    await page.goto('http://127.0.0.1:5173/task-trace', { waitUntil: 'networkidle' })
    evidence.defaultTimeRange = await page.locator('.ant-picker-range input').evaluateAll(elements => elements.map(el => el.value))
    evidence.defaultEventFilterEmpty = await page.locator('.ant-select-selection-item').count() === 0
    await page.locator('input[placeholder="任务编号（精确）"]').fill(evidence.taskCode)
    await page.locator('button').filter({ hasText: /查\s*询/ }).click()
    await page.getByText(evidence.taskCode).first().waitFor({ state: 'visible', timeout: 5000 })
    const item = page.locator('.ant-list-item').filter({ hasText: evidence.taskCode }).first()
    evidence.exactMatchVisible = await item.isVisible()
    await item.click()
    await page.getByText('计划版本列表').waitFor({ state: 'visible', timeout: 5000 })
    evidence.planHeaderCount = await page.locator('.ant-collapse-header').count()
    evidence.finalResultVisible = await page.getByText('最终结果').isVisible()
    evidence.timelineCount = await page.locator('.ant-timeline-item').count()
    await page.locator('.ant-collapse-header').first().click()
    await page.locator('.ant-collapse-item-active').first().waitFor({ state: 'visible', timeout: 5000 })
    evidence.expandedPlanText = await page.locator('.ant-collapse-content-active').first().innerText()
    evidence.stepDetailsVisible = /CAP_BAGGAGE_MEASURE|CAP_OVERSIZE_ALERT|步骤1|步骤2/.test(evidence.expandedPlanText)
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-084-trace-plan.png') })
    await page.locator('input[placeholder="任务编号（精确）"]').fill('TASK-DOES-NOT-EXIST')
    await page.locator('button').filter({ hasText: /查\s*询/ }).click()
    await page.getByText('未查询到符合条件的任务').waitFor({ state: 'visible', timeout: 5000 })
    evidence.emptyStateShown = true
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-084-trace-empty.png') })
  } finally { await app.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-084-trace.json'), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify(evidence) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
