// F028.R08: cross-read task 20 from admin audit and operator task trace.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const lines = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
function account(role) {
  const line = lines.find(value => value.startsWith(`|${role}|`))
  const [, , username, password] = line.split('|')
  return { username, password }
}
async function login(page, role) {
  const credentials = account(role)
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
  await page.locator('input[placeholder="账号"]').fill(credentials.username)
  await page.locator('input[placeholder="密码"]').fill(credentials.password)
  await page.locator('button[type="submit"]').click()
  await page.waitForURL('**/overview')
}

async function main() {
  const browser = await chromium.launch({ executablePath:
    'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome', taskId: 20 }
  try {
    const adminContext = await browser.newContext({ viewport: { width: 1366, height: 768 } })
    const admin = await adminContext.newPage()
    await login(admin, '系统管理员')
    await admin.goto('http://127.0.0.1:5173/operation-logs', { waitUntil: 'networkidle' })
    await admin.locator('.ant-select').first().click()
    await admin.getByText('人工处置', { exact: true }).last().click()
    const logRow = admin.locator('.ant-table-row').filter({ hasText: 'TASK-20261025-0020 -> MARK_FAILED' })
    await logRow.waitFor({ state: 'visible' })
    ev.audit = { route: new URL(admin.url()).pathname, rowText: await logRow.innerText() }
    await logRow.getByText('详情', { exact: true }).click()
    const modal = admin.locator('.ant-modal-content')
    await modal.waitFor({ state: 'visible' })
    ev.audit.modalText = await modal.innerText()
    ev.audit.screenshot = 'SRS_F028-R08-task20-audit.png'
    await modal.screenshot({ path: path.join(__dirname, 'evidence', ev.audit.screenshot) })

    const operatorContext = await browser.newContext({ viewport: { width: 1366, height: 768 } })
    const operator = await operatorContext.newPage()
    await login(operator, '运行操作员')
    await operator.goto('http://127.0.0.1:5173/task-trace', { waitUntil: 'networkidle' })
    const query = operator.locator('input[placeholder="任务编号（精确）"]')
    await query.fill('TASK-20261025-0020')
    await query.press('Enter')
    const taskRow = operator.locator('.ant-list-item').filter({ hasText: 'TASK-20261025-0020' })
    await taskRow.waitFor({ state: 'visible' })
    await taskRow.click()
    const timeline = operator.locator('.ant-card').filter({ hasText: '事件时间线' }).last()
    await timeline.locator('.ant-timeline-item').first().waitFor({ state: 'visible' })
    ev.trace = { route: new URL(operator.url()).pathname,
      taskRowText: await taskRow.innerText(),
      eventCount: await timeline.locator('.ant-timeline-item').count(),
      failedEvents: await timeline.locator('.ant-timeline-item').filter({ hasText: 'TASK_FAILED' }).allInnerTexts(),
      screenshot: 'SRS_F028-R08-task20-trace.png' }
    await operator.screenshot({ path: path.join(__dirname, 'evidence', ev.trace.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'SRS_F028-R08-task20-cross-trace-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ auditRow: ev.audit.rowText,
    traceRow: ev.trace.taskRowText, failedEvents: ev.trace.failedEvents.length,
    eventCount: ev.trace.eventCount }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
