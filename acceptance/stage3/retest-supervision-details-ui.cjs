// F020.R02: inspect a risk-downgraded task as the operations role.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')

async function main() {
  const browser = await chromium.launch({ executablePath:
    'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', taskId: 55 }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/tasks/55', { waitUntil: 'networkidle' })
    const planCard = page.locator('.ant-card').filter({ hasText: '计划版本与校验/判定结果' }).first()
    await planCard.locator('.ant-tabs-tab').first().waitFor({ state: 'visible' })
    ev.route = new URL(page.url()).pathname
    ev.taskCodeVisible = await page.getByText('TASK-20261026-0055').count()
    ev.taskHeader = await page.locator('.ant-descriptions').first().innerText()
    ev.tabs = await planCard.locator('.ant-tabs-tab').allInnerTexts()
    ev.planViews = []
    for (let index = 0; index < ev.tabs.length; index++) {
      await planCard.locator('.ant-tabs-tab').nth(index).click()
      ev.planViews.push({ tab: ev.tabs[index], text: await planCard.locator('.ant-tabs-tabpane-active').innerText() })
    }
    ev.screenshot = 'SRS_F020-R02-supervision-task55.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'SRS_F020-R02-supervision-task55.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ route: ev.route, taskCodeVisible: ev.taskCodeVisible,
    taskHeader: ev.taskHeader, tabs: ev.tabs,
    planViews: ev.planViews.map(view => ({ tab: view.tab, hasRiskCode:
      view.text.includes('RULE_RESOURCE_CRITICAL'), hasJudgmentBasis: view.text.includes('判定依据') })) }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
