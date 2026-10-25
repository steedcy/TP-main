// Fresh browser evidence for TC-031.S1 / TC-068.S1-S2 / AC-001.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const definition = JSON.parse(fs.readFileSync(path.join(__dirname, 'evidence/TC-068-dynamic-definition-api.json'), 'utf8'))
const name = definition.definitionName
const accounts = Object.fromEntries(fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .filter(line => /^\|(?:运行操作员|配置管理员)\|/.test(line))
  .map(line => { const [, role, username, password] = line.split('|'); return [role, { username, password }] }))

async function login(page, role) {
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
  await page.locator('input[placeholder="账号"]').fill(accounts[role].username)
  await page.locator('input[placeholder="密码"]').fill(accounts[role].password)
  await page.locator('button[type="submit"]').click()
  await page.waitForURL('**/overview')
}
async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', definitionName: name,
    definitionCode: definition.observations.definitionCode, config: {}, submit: {} }
  try {
    const config = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await login(config, '配置管理员')
    await config.goto('http://127.0.0.1:5173/task-definitions', { waitUntil: 'networkidle' })
    const row = config.locator('tr').filter({ hasText: name }).first()
    await row.waitFor({ state: 'visible' })
    ev.config.rowText = await row.innerText()
    ev.config.rowButtons = await row.locator('button').allInnerTexts()
    await row.locator('button').first().click()
    const modal = config.locator('.ant-modal-content').filter({ hasText: '编辑任务定义' })
    await modal.waitFor({ state: 'visible' })
    ev.config.paramName = await modal.locator('input[placeholder="参数名"]').inputValue()
    ev.config.paramType = await modal.locator('.ant-select-selection-item').allInnerTexts()
    ev.config.requiredChecked = await modal.locator('input[type="checkbox"]').first().isChecked()
    ev.config.range = await modal.locator('input[placeholder="取值范围/说明"]').inputValue()
    await config.screenshot({ path: path.join(__dirname, 'evidence/TC-068-definition-edit.png') })
    await config.close()

    const operator = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await login(operator, '运行操作员')
    await operator.goto('http://127.0.0.1:5173/tasks', { waitUntil: 'networkidle' })
    await operator.getByRole('button', { name: '提交任务', exact: true }).click()
    const submitModal = operator.locator('.ant-modal-content').filter({ hasText: '提交任务目标' })
    await submitModal.waitFor({ state: 'visible' })
    ev.submit.defaultGoal = await submitModal.locator('textarea').first().inputValue()
    ev.submit.emptyOkDisabled = await submitModal.locator('.ant-modal-footer button.ant-btn-primary').isDisabled()
    await submitModal.locator('.ant-select-selector').click()
    const option = operator.getByText(name, { exact: true }).last()
    await option.waitFor({ state: 'visible' })
    ev.submit.definitionSelectable = await option.isVisible()
    await option.click()
    await operator.keyboard.press('Escape')
    ev.submit.modalTextAfterSelect = await submitModal.innerText()
    ev.submit.sceneParamInputCount = await submitModal.locator('input[placeholder*="sampleLocation"]').count()
    ev.submit.sampleLocationLabelVisible = ev.submit.modalTextAfterSelect.includes('sampleLocation')
    ev.submit.goalTextareaCount = await submitModal.locator('textarea').count()
    await operator.screenshot({ path: path.join(__dirname, 'evidence/TC-031-068-submit-dynamic.png') })
    await operator.close()
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence/TC-031-068-dynamic-ui.json'), JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ config: ev.config, submit: { defaultGoal: ev.submit.defaultGoal,
    emptyOkDisabled: ev.submit.emptyOkDisabled, definitionSelectable: ev.submit.definitionSelectable,
    sceneParamInputCount: ev.submit.sceneParamInputCount, sampleLocationLabelVisible: ev.submit.sampleLocationLabelVisible } }) + '\n')
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1 })
