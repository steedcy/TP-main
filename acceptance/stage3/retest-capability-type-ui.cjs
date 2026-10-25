// TC-020.S1: current browser type choices and list columns for inherited simulator.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/devices/SIM_F2_DISPLAY/capabilities', { waitUntil: 'networkidle' })
    const result = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
      deviceCode: 'SIM_F2_DISPLAY', listRows: await page.locator('.ant-table-tbody .ant-table-row').count(),
      columnHeaders: await page.locator('.ant-table-thead th').allInnerTexts() }
    await page.getByRole('button', { name: '新增能力' }).click()
    const modal = page.locator('.ant-modal-content')
    await modal.waitFor({ state: 'visible' })
    await modal.locator('.ant-select-selector').first().click()
    await page.locator('.ant-select-item-option-content').first().waitFor({ state: 'visible' })
    result.typeOptions = await page.locator('.ant-select-item-option-content').allInnerTexts()
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-020-type-options.png') })
    fs.writeFileSync(path.join(__dirname, 'evidence/TC-020-type-options.json'), JSON.stringify(result, null, 2) + '\n')
    process.stdout.write(JSON.stringify(result) + '\n')
  } finally { await browser.close() }
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1 })
