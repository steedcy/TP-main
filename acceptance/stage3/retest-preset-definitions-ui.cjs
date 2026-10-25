// TC-069.S1: preset badges, deletion controls, and editable parameter form.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const [, , username, password] = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(line => line.startsWith('|配置管理员|')).split('|')
async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', presets: [] }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/task-definitions', { waitUntil: 'networkidle' })
    for (const name of ['超规行李处置', '特殊旅客服务', '航班变更应对']) {
      const row = page.locator('tr').filter({ hasText: name }).first()
      await row.waitFor({ state: 'visible' })
      ev.presets.push({ name, rowText: await row.innerText(),
        deleteButtonDisabled: await row.locator('button').last().isDisabled() })
    }
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-069-preset-list.png') })
    const row = page.locator('tr').filter({ hasText: '超规行李处置' }).first()
    await row.locator('button').first().click()
    const modal = page.locator('.ant-modal-content').filter({ hasText: '编辑任务定义' })
    await modal.waitFor({ state: 'visible' })
    ev.edit = { paramName: await modal.locator('input[placeholder="参数名"]').inputValue(),
      constraintValue: await modal.locator('textarea').nth(1).inputValue(),
      paramEditorPresent: await modal.getByRole('button', { name: '+ 添加参数' }).count() }
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-069-preset-editor.png') })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence/TC-069-preset-ui.json'), JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ presets: ev.presets.map(p => ({ name: p.name, deleteButtonDisabled: p.deleteButtonDisabled })), edit: ev.edit }) + '\n')
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1 })
