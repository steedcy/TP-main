// Browser evidence for TC-018.S3 and TC-019.S2; fixture is created by Python.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const config = JSON.parse(fs.readFileSync(path.join(root, '.local-test/stage3-template-used-ui.json')))
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
const mode = process.argv[2]
const code = mode === 'first' ? config.first : config.third

async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/devices/' + code + '/capabilities', { waitUntil: 'networkidle' })
    const result = { mode, deviceCode: code, title: await page.locator('.ant-page-header-heading-title').first().innerText(),
      templateSelectCount: await page.locator('.ant-select').count(),
      templateTextInBody: (await page.locator('body').innerText()).includes('基于标准能力模板新增') }
    if (mode === 'first') {
      await page.locator('.ant-select-selector').first().click()
      const option = page.getByText('阶段三已使用航显模板', { exact: false }).last()
      result.templateOptionVisible = await option.isVisible()
      await option.click()
      const modal = page.locator('.ant-modal-content')
      await modal.waitFor({ state: 'visible' })
      result.prefilledName = await modal.locator('input').nth(1).inputValue()
      result.prefilledDefault = await modal.locator('input[placeholder="默认值"]').nth(1).inputValue()
      await page.screenshot({ path: path.join(__dirname, 'evidence/TC-018-template-prefill.png') })
    } else {
      result.activeTemplateOptionCount = await page.getByText('阶段三已使用航显模板', { exact: false }).count()
      await page.screenshot({ path: path.join(__dirname, 'evidence/TC-019-inactive-template-excluded.png') })
    }
    process.stdout.write(JSON.stringify(result) + '\n')
  } finally {
    await browser.close()
  }
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1 })
