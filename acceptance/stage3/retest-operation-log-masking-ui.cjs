// F028.R06: inspect a device credential reference in the admin audit modal.
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
    await page.locator('.ant-select').first().click()
    await page.getByText('设备配置-新增', { exact: true }).last().click()
    const row = page.locator('.ant-table-row').filter({ hasText: 'S3_TC014_ALT_DISPLAY_B' })
    await row.waitFor({ state: 'visible' })
    ev.rowText = await row.innerText()
    await row.getByText('详情', { exact: true }).click()
    const modal = page.locator('.ant-modal-content')
    await modal.waitFor({ state: 'visible' })
    ev.detailText = await modal.innerText()
    ev.editDeleteControls = await modal.getByRole('button', { name: /编辑|修改|删除/ }).count()
    ev.screenshot = 'SRS_F028-R06-audit-masking-device.png'
    await modal.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot) })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'SRS_F028-R06-audit-masking-device.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ route: ev.route,
    rowText: ev.rowText, maskedCredentialVisible: /accessCredentialRef[\s\S]*\*/.test(ev.detailText),
    editDeleteControls: ev.editDeleteControls }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
