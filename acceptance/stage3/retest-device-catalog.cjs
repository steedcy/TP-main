// TC-008: live device list and create form defaults, filter/column presence.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')

async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome', viewport: '1366x768' }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/devices', { waitUntil: 'networkidle' })
    evidence.listHeaders = await page.locator('.ant-table-thead th').allInnerTexts()
    evidence.listRows = await page.locator('.ant-table-row').count()
    evidence.onlineFilterVisible = await page.getByText('按在线状态筛选').count() > 0
    evidence.onlineColumnVisible = evidence.listHeaders.some(x => /在线状态/.test(x))
    evidence.typeFilterVisible = await page.getByText('按设备类型筛选').count() > 0
    evidence.keywordFieldVisible = await page.locator('input[placeholder="按名称/编码检索"]').count() > 0
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-008-device-list.png') })
    await page.getByRole('button', { name: '新增设备' }).click()
    const modal = page.locator('.ant-modal-content')
    await modal.getByText('新增设备').waitFor({ state: 'visible' })
    evidence.defaultVirtuality = await modal.locator('.ant-radio-wrapper-checked').innerText()
    evidence.defaultType = await modal.locator('.ant-select-selection-item').first().innerText()
    evidence.regionInputVisible = await modal.locator('input[placeholder="如：T2-B区候机厅"]').isVisible()
    evidence.regionPresetDropdownVisible = await modal.locator('.ant-form-item').filter({ hasText: '所属区域' }).locator('.ant-select').count() > 0
    evidence.defaultPeriod = await modal.locator('.ant-input-number-input').last().inputValue()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-008-create-defaults.png') })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-008-device-catalog.json'), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify(evidence) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
