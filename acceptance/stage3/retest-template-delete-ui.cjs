// TC-019.S3: unused template delete cancellation, confirmation, list and audit.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
const base = 'http://127.0.0.1:8080/api/v1'
const code = 'S3_TC019_UNUSED'

async function main() {
  const loginResponse = await fetch(base + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }) })
  const token = (await loginResponse.json()).data.token
  const headers = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }
  const templatePath = `/device-types/SMART_DISPLAY/capability-templates/${code}`
  const request = async (path, method = 'GET', body) => {
    const response = await fetch(base + path, { method, headers, body: body ? JSON.stringify(body) : undefined })
    return { status: response.status, body: await response.json() }
  }
  const payload = { templateCode: code, templateName: '阶段三未使用删除验证', capabilityType: 'CAP_INFO_DISPLAY',
    inputParams: [{ name: 'contentData', type: 'String', required: true }],
    outputParams: [{ name: 'displayStatus', type: 'String', required: true }], templateDescription: '隔离验证' }
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', templateCode: code }
  const before = await request('/device-types/SMART_DISPLAY/capability-templates')
  if (before.body.data.some(row => row.templateCode === code)) throw Error('temporary code already exists')
  const created = await request('/device-types/SMART_DISPLAY/capability-templates', 'POST', payload)
  if (created.status !== 200) throw Error('fixture create failed: ' + created.status)
  evidence.createdUsageCount = created.body.data.usageCount
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/device-types', { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: '查看详情' }).first().click()
    const row = page.locator('.ant-drawer-content .ant-table-row').filter({ hasText: code })
    await row.waitFor({ state: 'visible' })
    evidence.rowVisibleBefore = true
    await row.getByRole('button', { name: '删除' }).click()
    await page.getByText('确认删除该能力模板？').waitFor({ state: 'visible' })
    evidence.confirmPromptVisible = true
    const buttons = page.locator('.ant-popconfirm-buttons button')
    evidence.confirmButtonLabels = await buttons.allInnerTexts()
    await buttons.first().click()
    evidence.rowVisibleAfterCancel = await row.isVisible()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-019-unused-after-cancel.png') })
    await row.getByRole('button', { name: '删除' }).click()
    await page.getByText('确认删除该能力模板？').waitFor({ state: 'visible' })
    await page.locator('.ant-popconfirm-buttons button').last().click()
    await row.waitFor({ state: 'detached', timeout: 8000 })
    evidence.rowAbsentAfterConfirm = true
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-019-unused-after-delete.png') })
  } finally {
    await browser.close()
    const remaining = await request('/device-types/SMART_DISPLAY/capability-templates')
    evidence.apiAbsentAfter = !remaining.body.data.some(row => row.templateCode === code)
    if (!evidence.apiAbsentAfter) await request(templatePath, 'DELETE')
  }
  const logs = await request('/operation-logs?operationType=CAPABILITY_TEMPLATE_DELETE&page=1&size=100')
  evidence.deleteAuditPresent = logs.body.data.content.some(row => String(row.operationTarget).includes(code) && row.operationResult === 'SUCCESS')
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-019-unused-delete.json'), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify(evidence) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
