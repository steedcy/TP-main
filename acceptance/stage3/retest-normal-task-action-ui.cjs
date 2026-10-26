// TC-064.S1: active normal execution exposes only business termination.
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
    ev.statusText = (await page.locator('body').innerText()).match(/执行中|待人工处理|已完成/)?.[0] || null
    ev.manualActionCardCount = await page.locator('.ant-card').filter({ hasText: '待人工处理' }).count()
    ev.actions = Object.fromEntries(await Promise.all(
      ['转基线执行', '重试规划', '置为失败', '终止任务'].map(async name =>
        [name, await page.getByRole('button', { name }).count()])))
    ev.confirmationButtonCount = await page.getByRole('button', { name: /确认.*执行|人工确认/ }).count()
    ev.screenshot = `TC-064-normal-executing-${taskId}.png`
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', `TC-064-normal-executing-${taskId}.json`),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ taskId, route: ev.route, statusText: ev.statusText,
    manualActionCardCount: ev.manualActionCardCount, actions: ev.actions,
    confirmationButtonCount: ev.confirmationButtonCount }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
