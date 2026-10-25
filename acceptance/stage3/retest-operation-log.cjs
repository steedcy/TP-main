// TC-085: live admin audit filters, scope, detail masking, and empty state.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const accounts = Object.fromEntries(fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .filter(line => /^\|(?:系统管理员|运行操作员|配置管理员)\|/.test(line))
  .map(line => { const [, role, username, password] = line.split('|'); return [role, { username, password }] }))
const api = 'http://127.0.0.1:8080/api/v1'
async function token(role) {
  const response = await fetch(api + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(accounts[role]) })
  return (await response.json()).data.token
}
async function list(q, auth) {
  const response = await fetch(api + '/operation-logs?' + q, { headers: { Authorization: 'Bearer ' + auth } })
  return (await response.json()).data
}
async function main() {
  const admin = await token('系统管理员')
  const operator = await token('运行操作员')
  const config = await token('配置管理员')
  const q = 'username=oprator&operationType=LOGIN&operationResult=SUCCESS&page=1&size=100'
  const filtered = await list(q, admin)
  const operatorOverride = await list('username=admin&page=1&size=100', operator)
  const configOverride = await list('username=admin&page=1&size=100', config)
  const changeRows = await list('operationType=USER_STATUS_CHANGE&page=1&size=100', admin)
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    api: { filteredCount: filtered.totalElements,
      filteredAllMatch: filtered.content.every(r => r.username === 'oprator' && r.operationType === 'LOGIN' && r.operationResult === 'SUCCESS'),
      operatorOnlyOwn: operatorOverride.content.every(r => r.username === 'oprator'),
      configOnlyOwn: configOverride.content.every(r => r.username === 'set'),
      changedAccountRows: changeRows.totalElements,
      changedAccountHasDetail: changeRows.content.some(r => r.detail) }, browser: {} }
  const app = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  try {
    const page = await app.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(accounts['系统管理员'].username)
    await page.locator('input[placeholder="密码"]').fill(accounts['系统管理员'].password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/operation-logs', { waitUntil: 'networkidle' })
    evidence.browser.defaultTimeRange = await page.locator('.ant-picker-range input').evaluateAll(elements => elements.map(el => el.value))
    evidence.browser.defaultUserEmpty = await page.locator('input[placeholder="操作账号"]').inputValue() === ''
    evidence.browser.rowsInitiallyVisible = await page.locator('.ant-table-row').count()
    await page.locator('.ant-table-row').first().getByText('详情').click()
    await page.getByText('操作详情').waitFor({ state: 'visible' })
    const detail = await page.locator('.ant-modal-content').innerText()
    evidence.browser.detailHasActorTimeIp = /操作时间/.test(detail) && /操作人/.test(detail) && /来源IP/.test(detail)
    evidence.browser.detailContainsRealPassword = Object.values(accounts).some(a => detail.includes(a.password))
    evidence.browser.editDeleteControls = await page.locator('.ant-modal-content button').filter({ hasText: /编辑|删除/ }).count()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-085-audit-detail.png') })
    await page.locator('.ant-modal-close').click()
    await page.locator('input[placeholder="操作账号"]').fill('S3_NO_SUCH_ACCOUNT_999')
    await page.locator('button').filter({ hasText: /查\s*询/ }).click()
    await page.waitForTimeout(700)
    evidence.browser.emptyText = await page.locator('.ant-table-placeholder').innerText().catch(() => '')
    evidence.browser.emptyStateVisible = (await page.locator('.ant-table-row').count()) === 0
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-085-audit-empty.png') })
  } finally { await app.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-085-operation-log.json'), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify(evidence) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
