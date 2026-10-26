// TC-043.S1: inspect the risk-rule configuration page against a fresh temporary rule.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
const code = process.argv[2]
if (!/^S3_TC043_[A-Z0-9_]+$/.test(code || '')) throw new Error('Temporary rule code required')

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', ruleCode: code }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/risk-rules', { waitUntil: 'networkidle' })
    const row = page.locator('.ant-table-row').filter({ hasText: code })
    await row.waitFor({ state: 'visible' })
    ev.route = new URL(page.url()).pathname
    ev.headers = await page.locator('.ant-table-thead th').allInnerTexts()
    ev.temporaryRow = await row.innerText()
    ev.pageButtons = await page.locator('button').allInnerTexts()
    ev.createButtonCount = await page.locator('button').filter({ hasText: /新增|添加|创建/ }).count()
    ev.editButtonCount = await row.locator('button').filter({ hasText: /编辑/ }).count()
    ev.switchCount = await row.locator('.ant-switch').count()
    ev.screenshot = 'TC-043-risk-rule-ui.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-043-risk-rule-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ route: ev.route, headers: ev.headers,
    createButtonCount: ev.createButtonCount, editButtonCount: ev.editButtonCount,
    switchCount: ev.switchCount }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
