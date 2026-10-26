// TC-066.S1: verify 200-character limit and canceled modal on task 20.
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
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', taskId: 20, terminatePosts: [] }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    page.on('request', request => {
      if (request.url().includes('/tasks/20/terminate') && request.method() === 'POST')
        ev.terminatePosts.push(request.url())
    })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/tasks/20', { waitUntil: 'networkidle' })
    ev.route = new URL(page.url()).pathname
    await page.getByRole('button', { name: '终止任务' }).first().click()
    const modal = page.locator('.ant-modal:visible')
    const textarea = modal.locator('textarea')
    ev.maxLengthAttribute = await textarea.getAttribute('maxlength')
    ev.emptyDisabled = await modal.locator('.ant-modal-footer .ant-btn-primary').isDisabled()
    await textarea.fill('X'.repeat(201))
    ev.lengthAfter201Input = (await textarea.inputValue()).length
    await modal.locator('input[type="checkbox"]').check()
    ev.checkedEnabled = await modal.locator('.ant-modal-footer .ant-btn-primary').isEnabled()
    await modal.locator('.ant-modal-footer button:not(.ant-btn-primary)').click()
    await page.locator('.ant-modal:visible').waitFor({ state: 'hidden' })
    ev.closedAfterCancel = await page.locator('.ant-modal:visible').count() === 0
    await page.waitForTimeout(500)
    ev.terminatePostCountAfterCancel = ev.terminatePosts.length
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-066-terminate-modal-boundary.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ taskId: 20, maxLengthAttribute: ev.maxLengthAttribute,
    lengthAfter201Input: ev.lengthAfter201Input, closedAfterCancel: ev.closedAfterCancel,
    terminatePostCountAfterCancel: ev.terminatePostCountAfterCancel }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
