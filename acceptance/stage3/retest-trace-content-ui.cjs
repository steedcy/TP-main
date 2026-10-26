// TC-084.S2: inspect the task 19 trace chronology, fields and retained versions.
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
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome', taskId: 19 }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/task-trace', { waitUntil: 'networkidle' })
    ev.route = new URL(page.url()).pathname
    const queryInput = page.locator('input[placeholder="任务编号（精确）"]')
    await queryInput.fill('TASK-20261025-0019')
    await queryInput.press('Enter')
    const row = page.locator('.ant-list-item').filter({ hasText: 'TASK-20261025-0019' })
    await row.waitFor({ state: 'visible' })
    await row.click()
    const versions = page.locator('.ant-card').filter({ hasText: '计划版本列表' }).first()
    await versions.locator('.ant-collapse-header').first().waitFor({ state: 'visible' })
    ev.versionHeaders = await versions.locator('.ant-collapse-header').allInnerTexts()
    const timeline = page.locator('.ant-card').filter({ hasText: '事件时间线' }).last()
    await timeline.locator('.ant-timeline-item').first().waitFor({ state: 'visible' })
    ev.eventTexts = await timeline.locator('.ant-timeline-item').allInnerTexts()
    ev.eventEditControls = await timeline.getByRole('button', { name: /编辑|修改|删除/ }).count()
    ev.eventEditableElements = await timeline.locator('.ant-timeline [contenteditable="true"],.ant-timeline input,.ant-timeline textarea').count()
    ev.screenshot = 'TC-084-S2-trace-content-task19.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-084-S2-trace-content-task19.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ route: ev.route, versionHeaders: ev.versionHeaders,
    eventCount: ev.eventTexts.length, eventEditControls: ev.eventEditControls,
    eventEditableElements: ev.eventEditableElements }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
