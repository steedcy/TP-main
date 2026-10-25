// TC-068.S2: disabled extension remains in history filter but leaves submit choices.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const definition = JSON.parse(fs.readFileSync(path.join(__dirname, 'evidence/TC-068-dynamic-definition-api.json'), 'utf8'))
const [, , username, password] = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(line => line.startsWith('|运行操作员|')).split('|')
async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    definitionName: definition.definitionName, observations: {} }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/tasks', { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: '提交任务', exact: true }).click()
    const modal = page.locator('.ant-modal-content').filter({ hasText: '提交任务目标' })
    await modal.locator('.ant-select-selector').click()
    ev.observations.disabledInSubmitOptions = await page.locator('.ant-select-dropdown:visible')
      .getByText(definition.definitionName, { exact: true }).count()
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-068-disabled-submit.png') })
    await page.goto('http://127.0.0.1:5173/tasks', { waitUntil: 'networkidle' })
    await page.locator('.ant-select').nth(1).locator('.ant-select-selector').click()
    await page.locator('.ant-select-dropdown:visible').waitFor({ state: 'visible' })
    ev.observations.historicalFilterDropdownText = await page.locator('.ant-select-dropdown:visible').innerText()
    ev.observations.inHistoricalFilter = await page.locator('.ant-select-dropdown:visible')
      .getByText(definition.definitionName, { exact: true }).count()
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-068-disabled-history-filter.png') })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence/TC-068-disabled-ui.json'), JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify(ev) + '\n')
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1 })
