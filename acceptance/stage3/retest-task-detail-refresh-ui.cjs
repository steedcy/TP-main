// F020.R09: sample actual task-detail GET cadence while a dry-run executes.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const taskId = Number(process.argv[2])
if (!Number.isInteger(taskId) || taskId < 1) throw new Error('Task ID required')

async function main() {
  const browser = await chromium.launch({ executablePath:
    'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', taskId, taskGetResponses: [] }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    page.on('response', async response => {
      if (response.request().method() !== 'GET' ||
          new URL(response.url()).pathname !== `/api/v1/tasks/${taskId}`) return
      const at = new Date().toISOString()
      let taskStatus = null
      try {
        const body = await response.json()
        taskStatus = body.data?.status ?? body.status ?? null
      } catch (_) { /* response status remains in evidence */ }
      ev.taskGetResponses.push({ at, httpStatus: response.status(), taskStatus })
    })
    await page.goto(`http://127.0.0.1:5173/tasks/${taskId}`, { waitUntil: 'networkidle' })
    ev.route = new URL(page.url()).pathname
    ev.initialStatusText = (await page.locator('body').innerText()).match(/执行中|已完成|人工终止/)?.[0] || null
    ev.initialAt = new Date().toISOString()
    await page.waitForTimeout(24000)
    ev.finalStatusText = (await page.locator('body').innerText()).match(/执行中|已完成|人工终止/)?.[0] || null
    ev.finalAt = new Date().toISOString()
    ev.screenshot = `SRS_F020-R09-refresh-task${taskId}.png`
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', `SRS_F020-R09-refresh-task${taskId}.json`),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ taskId, route: ev.route,
    initialStatusText: ev.initialStatusText, finalStatusText: ev.finalStatusText,
    taskGetResponses: ev.taskGetResponses }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
