// TC-064.S2: perform the MARK_FAILED branch on fictional pending-manual task 20.
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
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome', taskId: 20 }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/tasks/20', { waitUntil: 'networkidle' })
    ev.route = new URL(page.url()).pathname
    ev.beforeStatus = await page.locator('.ant-descriptions .ant-tag').first().innerText()
    ev.markFailedButtonCount = await page.getByRole('button', { name: '置为失败' }).count()
    ev.beforeScreenshot = 'TC-064-mark-failed-task20-before.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.beforeScreenshot), fullPage: true })
    if (ev.beforeStatus !== '待人工处理' || ev.markFailedButtonCount !== 1)
      throw new Error('Task 20 is not ready for MARK_FAILED')
    const responsePromise = page.waitForResponse(response =>
      new URL(response.url()).pathname === '/api/v1/tasks/20/manual-actions' &&
      response.request().method() === 'POST')
    await page.getByRole('button', { name: '置为失败' }).click()
    const response = await responsePromise
    ev.actionHttpStatus = response.status()
    const body = await response.json()
    ev.actionResultStatus = body.data?.status ?? null
    await page.waitForFunction(() => document.querySelector('.ant-descriptions .ant-tag')?.innerText === '失败')
    ev.afterStatus = await page.locator('.ant-descriptions .ant-tag').first().innerText()
    ev.afterActionCount = await page.getByRole('button', { name: '置为失败' }).count()
    ev.afterScreenshot = 'TC-064-mark-failed-task20-after.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.afterScreenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-064-mark-failed-task20-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ beforeStatus: ev.beforeStatus,
    actionHttpStatus: ev.actionHttpStatus, actionResultStatus: ev.actionResultStatus,
    afterStatus: ev.afterStatus, afterActionCount: ev.afterActionCount }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
