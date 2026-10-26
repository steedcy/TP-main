// TC-011.S2: verify that a configuration administrator can reach the task link target.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const accounts = Object.fromEntries(fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .filter(line => /^\|(?:配置管理员|运行操作员)\|/.test(line))
  .map(line => { const [, role, username, password] = line.split('|'); return [role, { username, password }] }))
const taskId = Number(process.argv[2])
if (!Number.isInteger(taskId)) throw new Error('Task ID required')

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', taskId, roles: {} }
  try {
    for (const role of ['配置管理员', '运行操作员']) {
      const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
      await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
      await page.locator('input[placeholder="账号"]').fill(accounts[role].username)
      await page.locator('input[placeholder="密码"]').fill(accounts[role].password)
      await page.locator('button[type="submit"]').click()
      await page.waitForURL('**/overview')
      await page.goto(`http://127.0.0.1:5173/tasks/${taskId}`, { waitUntil: 'networkidle' })
      ev.roles[role] = { finalRoute: new URL(page.url()).pathname,
        taskDetailVisible: (await page.locator('body').innerText()).includes(`任务 #${taskId}`) }
      await page.close()
    }
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-011-task-link-role.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify(ev.roles) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
