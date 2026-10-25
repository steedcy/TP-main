// TC-025/026: unsaved browser editor operations and sequential-only controls.
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
    await page.goto('http://127.0.0.1:5173/baseline-templates', { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: '新增模板' }).click()
    const modal = page.locator('.ant-modal-content')
    await modal.waitFor({ state: 'visible' })
    const result = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
      sequentialCaption: await modal.getByText('步骤（顺序执行，最多5个）').isVisible() }
    const add = modal.getByRole('button', { name: /添加步骤/ })
    await add.click()
    await add.click()
    const conditions = modal.locator('input[placeholder="描述判定该步骤完成的输出条件"]')
    await conditions.nth(0).fill('first-condition')
    await conditions.nth(1).fill('second-condition')
    result.defaultTimeouts = await modal.locator('.ant-input-number-input').evaluateAll(nodes => nodes.map(x => x.value))
    result.buttonsBeforeMove = await modal.locator('button').allInnerTexts()
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-025-026-baseline-editor-before-move.png') })
    await modal.locator('button').filter({ hasText: /上\s*移/ }).last().click()
    result.afterUp = await conditions.evaluateAll(nodes => nodes.map(x => x.value))
    await modal.locator('button').filter({ hasText: /下\s*移/ }).first().click()
    result.afterDown = await conditions.evaluateAll(nodes => nodes.map(x => x.value))
    await modal.locator('button').filter({ hasText: /删\s*除/ }).first().click()
    result.afterDeleteCount = await conditions.count()
    for (let i = 0; i < 4; i++) await add.click()
    result.fiveStepCount = await conditions.count()
    result.sixthStepButtonDisabled = await add.isDisabled()
    result.motionOrComplexControls = []
    for (const term of ['并行', '条件分支', '循环', '补偿', '拖拽']) {
      if (await modal.locator('button').filter({ hasText: term }).count()) result.motionOrComplexControls.push(term)
    }
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-025-026-baseline-editor.png'), fullPage: true })
    fs.writeFileSync(path.join(__dirname, 'evidence/TC-025-026-baseline-editor.json'), JSON.stringify(result, null, 2) + '\n')
    process.stdout.write(JSON.stringify(result) + '\n')
  } finally { await browser.close() }
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1 })
