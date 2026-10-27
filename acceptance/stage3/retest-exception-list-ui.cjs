// TC-058.S2: inspect the live operator exception list, filters and task link.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const accountLine = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(line => /^\|运行操作员\|/.test(line))
const [, , username, password] = accountLine.split('|')

async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome',
    requests: [], filters: {}, navigation: {} }
  page.on('response', response => {
    if (response.url().includes('/api/v1/task-exceptions')) {
      evidence.requests.push({ url: response.url(), status: response.status() })
    }
  })
  try {
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/task-exceptions', { waitUntil: 'networkidle' })
    evidence.defaultRows = await page.locator('tbody tr').allInnerTexts()
    evidence.headers = await page.locator('thead th').allInnerTexts()
    evidence.selects = await page.locator('.ant-select').count()
    evidence.historyControl = await page.getByText('历史列表', { exact: true }).count()
    evidence.reasonCodeVisible = evidence.headers.some(h => h.includes('原因码'))
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-058-exception-list-default.png') })
    const typeSelect = page.locator('.ant-select').first()
    for (const label of ['设备离线', '能力缺口', '执行超时', '步骤失败', '重新规划失败']) {
      await typeSelect.click()
      await page.locator('.ant-select-dropdown:visible').getByText(label, { exact: true }).click()
      await page.waitForTimeout(250)
      evidence.filters[label] = { rows: await page.locator('tbody tr').allInnerTexts(),
        selected: await typeSelect.innerText() }
    }
    await typeSelect.locator('.ant-select-clear').click()
    await page.waitForTimeout(250)
    const taskLink = page.locator('tbody tr a[href^="/tasks/"]').first()
    evidence.navigation.linkCount = await taskLink.count()
    if (evidence.navigation.linkCount) {
      evidence.navigation.href = await taskLink.getAttribute('href')
      await taskLink.click()
      await page.waitForURL('**/tasks/*')
      evidence.navigation.landed = page.url()
    }
  } finally {
    const out = path.join(__dirname, 'evidence', 'TC-058-exception-list-ui-' +
      evidence.observedAt.replace(/[-:.]/g, '').replace(/\d{3}Z$/, 'Z') + '.json')
    fs.writeFileSync(out, JSON.stringify(evidence, null, 2) + '\n')
    console.log(JSON.stringify({ evidence: path.basename(out), defaultRows: evidence.defaultRows,
      headers: evidence.headers, filters: Object.keys(evidence.filters), navigation: evidence.navigation }))
    await browser.close()
  }
}
main().catch(error => { console.error(String(error)); process.exitCode = 1 })
