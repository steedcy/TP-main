// TC-085.S2: verify an empty admin operation-log query displays an empty state.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|系统管理员|'))
const [, , username, password] = line.split('|')

async function main() {
  const browser = await chromium.launch({ executablePath:
    'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome' }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/operation-logs', { waitUntil: 'networkidle' })
    ev.route = new URL(page.url()).pathname
    ev.queryUsername = 'S3_STAGE3_EMPTY_AUDIT_QUERY_20261027'
    const input = page.locator('input[placeholder="操作账号"]')
    await input.fill(ev.queryUsername)
    await input.press('Enter')
    await page.locator('.ant-empty').first().waitFor({ state: 'visible' })
    ev.rowCount = await page.locator('.ant-table-row').count()
    ev.emptyText = await page.locator('.ant-empty').first().innerText()
    ev.screenshot = 'TC-085-S2-empty-audit-query.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-085-S2-empty-audit-query.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ route: ev.route, rowCount: ev.rowCount,
    emptyText: ev.emptyText }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
