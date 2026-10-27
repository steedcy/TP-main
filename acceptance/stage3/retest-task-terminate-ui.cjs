// TC-066.S1: exercise the live termination modal during a delayed dry-run.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const taskId = Number(process.argv[2])
if (!Number.isInteger(taskId) || taskId < 1) throw new Error('Task ID required')
const evidencePrefix = taskId === 64 ? 'TC-066' : 'TC-064'

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', taskId }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto(`http://127.0.0.1:5173/tasks/${taskId}`, { waitUntil: 'networkidle' })
    ev.route = new URL(page.url()).pathname
    ev.taskStatusBefore = (await page.locator('body').innerText()).match(/执行中|待人工处理|已完成|人工终止/)?.[0] || null
    const open = page.getByRole('button', { name: '终止任务' }).first()
    ev.terminateButtonCount = await page.getByRole('button', { name: '终止任务' }).count()
    await open.click()
    let modal = page.locator('.ant-modal:visible')
    ev.modalVisible = await modal.isVisible()
    ev.warningText = await modal.locator('.ant-alert').innerText()
    const confirm = modal.locator('.ant-modal-footer .ant-btn-primary')
    ev.emptyReasonDisabled = await confirm.isDisabled()
    await modal.locator('textarea').fill('阶段3人工终止边界复测')
    ev.uncheckedDisabled = await confirm.isDisabled()
    await modal.locator('.ant-modal-footer button:not(.ant-btn-primary)').click()
    ev.cancelClosedModal = await modal.isHidden()
    await open.click()
    modal = page.locator('.ant-modal:visible')
    await modal.locator('textarea').fill('阶段3人工终止边界复测')
    await modal.locator('input[type="checkbox"]').check()
    ev.checkedEnabled = await modal.locator('.ant-modal-footer .ant-btn-primary').isEnabled()
    ev.screenshot = `${evidencePrefix}-terminate-modal-${taskId}.png`
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
    const responsePromise = page.waitForResponse(r =>
      r.url().includes(`/tasks/${taskId}/terminate`) && r.request().method() === 'POST',
      { timeout: 65000 })
    await modal.locator('.ant-modal-footer .ant-btn-primary').click()
    const response = await responsePromise
    ev.confirmHttpStatus = response.status()
    ev.confirmResponseCode = (await response.json()).code
    await page.waitForTimeout(800)
    ev.modalClosedAfterConfirm = await page.locator('.ant-modal:visible').count() === 0
    ev.bodyAfter = (await page.locator('body').innerText()).slice(-1000)
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', `${evidencePrefix}-terminate-ui-${taskId}.json`),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ taskId, route: ev.route,
    terminateButtonCount: ev.terminateButtonCount, modalVisible: ev.modalVisible,
    emptyReasonDisabled: ev.emptyReasonDisabled, uncheckedDisabled: ev.uncheckedDisabled,
    cancelClosedModal: ev.cancelClosedModal, checkedEnabled: ev.checkedEnabled,
    confirmHttpStatus: ev.confirmHttpStatus, confirmResponseCode: ev.confirmResponseCode }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
