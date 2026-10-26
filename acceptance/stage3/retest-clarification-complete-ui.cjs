// TC-032.S1: answer the missing location in the browser's per-question field.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const start = JSON.parse(fs.readFileSync(path.join(__dirname, 'evidence/TC-032-complete-start.json'), 'utf8'))
const task = start.observations.task
if (task.status !== 'PLANNING' || !task.missingInfoQuestions?.length) throw new Error('task is not awaiting clarification')
const [, , username, password] = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(line => line.startsWith('|运行操作员|')).split('|')
async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', taskId: task.id,
    taskCode: task.taskCode, questions: task.missingInfoQuestions, observations: {} }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/tasks', { waitUntil: 'networkidle' })
    const row = page.locator('tr').filter({ hasText: task.taskCode }).first()
    await row.waitFor({ state: 'visible' })
    await row.getByText('补充信息', { exact: true }).click()
    const modal = page.locator('.ant-modal-content').filter({ hasText: '补充信息' })
    await modal.waitFor({ state: 'visible' })
    ev.observations.modalText = await modal.innerText()
    ev.observations.questionInputCount = await modal.locator('input').count()
    ev.observations.initialSubmitDisabled = await modal.locator('.ant-modal-footer button.ant-btn-primary').isDisabled()
    const input = modal.locator('input').first()
    await input.fill('F2_BAGGAGE_POINT')
    ev.observations.answer = await input.inputValue()
    ev.observations.filledSubmitEnabled = await modal.locator('.ant-modal-footer button.ant-btn-primary').isEnabled()
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-032-complete-clarify-before.png') })
    const responsePromise = page.waitForResponse(response => response.url().includes('/tasks/' + task.id + '/clarify') && response.request().method() === 'POST')
    await modal.locator('.ant-modal-footer button.ant-btn-primary').click()
    const response = await responsePromise
    ev.observations.clarifyRequestBody = response.request().postDataJSON()
    ev.observations.clarifyHttp = response.status()
    ev.observations.clarifyResponse = await response.json()
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-032-complete-clarify-after.png') })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence/TC-032-complete-ui.json'), JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ taskId: task.id, questionInputCount: ev.observations.questionInputCount,
    initialSubmitDisabled: ev.observations.initialSubmitDisabled,
    filledSubmitEnabled: ev.observations.filledSubmitEnabled,
    clarifyHttp: ev.observations.clarifyHttp,
    responseStatus: ev.observations.clarifyResponse?.data?.status }) + '\n')
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1 })
