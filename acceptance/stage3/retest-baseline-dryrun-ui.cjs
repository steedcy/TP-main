// TC-028 browser dry-run result and enable; existing isolated template is restored disabled.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
const base = 'http://127.0.0.1:8080/api/v1'
const name = 'S3_TC028_DISPLAY_DRYRUN'

async function main() {
  const login = await fetch(base + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }) })
  const token = (await login.json()).data.token
  const headers = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }
  const request = async (url, method = 'GET', body) => {
    const r = await fetch(base + url, { method, headers, body: body ? JSON.stringify(body) : undefined })
    return { status: r.status, body: await r.json() }
  }
  const list = await request('/baseline-templates')
  const template = list.body.data.find(x => x.templateName === name)
  if (!template || template.templateStatus !== 'DISABLED') throw Error('expected disabled isolated template')
  const detail = await request('/baseline-templates/' + template.id)
  const edited = await request('/baseline-templates/' + template.id, 'PUT', {
    inputParams: detail.body.data.inputParams, steps: detail.body.data.steps })
  if (edited.status !== 200 || edited.body.data.templateStatus !== 'DRAFT') throw Error('draft update failed')
  const agents = await request('/device-agents?page=1&size=100')
  const agent = agents.body.data.content.find(x => x.deviceCode === 'SIM_F2_DISPLAY')
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', templateName: name,
    templateId: template.id, editedVersion: edited.body.data.templateVersion, agentId: agent.agentId }
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/baseline-templates', { waitUntil: 'networkidle' })
    const row = page.locator('.ant-table-tbody .ant-table-row').filter({ hasText: name })
    await row.getByRole('button', { name: '试运行' }).click()
    const modal = page.locator('.ant-modal-content').filter({ hasText: '试运行' })
    await modal.waitFor({ state: 'visible' })
    evidence.versionVisible = (await modal.innerText()).includes(evidence.editedVersion)
    evidence.defaultInputs = await modal.locator('input').evaluateAll(nodes => nodes.map(x => x.value).filter(Boolean))
    await modal.locator('.ant-select-selector').first().click()
    await page.locator('.ant-select-item-option-content').filter({ hasText: agent.agentId }).first().click()
    const responsePromise = page.waitForResponse(r => r.url().includes('/baseline-templates/' + template.id + '/dry-run') && r.request().method() === 'POST')
    await modal.getByRole('button', { name: '开始试运行' }).click()
    const response = await responsePromise
    const started = await response.json()
    evidence.startHttpStatus = response.status()
    evidence.taskId = started.data.taskId
    evidence.startedResult = started.data.result
    await modal.getByText('总体结果: 成功').waitFor({ state: 'visible', timeout: 30000 })
    evidence.resultVisible = true
    evidence.stepRows = await modal.locator('.ant-table-tbody .ant-table-row').count()
    evidence.durationHeaderVisible = (await modal.innerText()).includes('耗时(秒)')
    evidence.eventsVisible = await modal.locator('.ant-timeline-item').count()
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-028-baseline-dryrun-ui.png') })
    await modal.locator('.ant-modal-close').click()
    evidence.rowTextAfterTrial = await row.innerText()
    evidence.rowButtonsAfterTrial = await row.locator('button').allInnerTexts()
    await row.locator('button').filter({ hasText: /启\s*用/ }).first().click()
    evidence.statusAfterEnable = (await request('/baseline-templates/' + template.id)).body.data.templateStatus
  } finally {
    await browser.close()
    const disable = await request('/baseline-templates/' + template.id + '/disable', 'POST')
    evidence.disableHttpStatus = disable.status
    evidence.finalStatus = (await request('/baseline-templates/' + template.id)).body.data.templateStatus
    fs.writeFileSync(path.join(__dirname, 'evidence/TC-028-baseline-dryrun-ui.json'), JSON.stringify(evidence, null, 2) + '\n')
  }
  process.stdout.write(JSON.stringify(evidence) + '\n')
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1 })
