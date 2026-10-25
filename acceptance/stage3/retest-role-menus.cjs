// TC-003.S1: live role menus and allowed page navigation.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const rows = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .filter(line => /^\|(?:系统管理员|运行操作员|配置管理员)\|/.test(line))
const accounts = rows.map(line => { const [, role, username, password] = line.split('|'); return { role, username, password } })
const expected = {
  '系统管理员': { required: ['运行总览', '账号管理', '标准演示数据复位', '操作记录'], forbidden: ['设备管理', '任务管理'] },
  '配置管理员': { required: ['运行总览', '设备管理', '基线模板', '任务定义', '风险规则配置'], forbidden: ['账号管理', '任务管理'] },
  '运行操作员': { required: ['运行总览', '任务管理', '异常处置', '过程追溯'], forbidden: ['账号管理', '设备管理'] },
}
async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const evidence = { observedAt: new Date().toISOString(), gitHead: '0d798ceb53bc37498f353b4796f2081b92e2011b',
    browser: 'Chrome', viewport: '1366x768', roles: [] }
  try {
    for (const account of accounts) {
      const context = await browser.newContext({ viewport: { width: 1366, height: 768 } })
      const page = await context.newPage()
      await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
      await page.locator('input[placeholder="账号"]').fill(account.username)
      await page.locator('input[placeholder="密码"]').fill(account.password)
      await page.locator('button[type="submit"]').click()
      await page.waitForURL('**/overview', { timeout: 8000 })
      const menus = await page.locator('.ant-layout-sider .ant-menu-item').allInnerTexts()
      const allow = expected[account.role]
      const result = { role: account.role, username: account.username, menus,
        requiredVisible: allow.required.every(item => menus.includes(item)),
        forbiddenHidden: allow.forbidden.every(item => !menus.includes(item)) }
      const route = account.role === '系统管理员' ? '/users'
        : account.role === '配置管理员' ? '/devices' : '/tasks'
      await page.goto('http://127.0.0.1:5173' + route, { waitUntil: 'networkidle' })
      result.allowedPageLoaded = new URL(page.url()).pathname === route
      await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-003-S1-' + account.username + '.png') })
      evidence.roles.push(result)
      await context.close()
    }
  } finally { await browser.close() }
  evidence.pass = evidence.roles.length === 3 && evidence.roles.every(row =>
    row.requiredVisible && row.forbiddenHidden && row.allowedPageLoaded)
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-003-role-menus.json'), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ pass: evidence.pass, roles: evidence.roles }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
