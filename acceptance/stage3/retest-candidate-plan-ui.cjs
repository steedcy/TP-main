// TC-037.S1: inspect the candidate plan actually rendered for task 55.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const accountLine = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(line => line.startsWith('|运行操作员|'))
const [, , username, password] = accountLine.split('|')

async function main() {
  const app = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome',
    viewport: '1366x768', taskId: 55, taskSource: 'controlled planning fixture',
    route: null, versionTabs: [], candidateHeaders: [], candidateRows: [],
    contextHeaderCount: 0, visibleLabels: {}, screenshot: null }
  try {
    const page = await app.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview', { timeout: 8000 })
    await page.goto('http://127.0.0.1:5173/tasks/55', { waitUntil: 'networkidle' })
    await page.getByText('计划版本与校验/判定结果').waitFor({ state: 'visible', timeout: 8000 })
    ev.route = new URL(page.url()).pathname
    ev.versionTabs = await page.locator('.ant-tabs-tab').allInnerTexts()
    const planCard = page.locator('.ant-card').filter({ hasText: '计划版本与校验/判定结果' }).first()
    const activePane = planCard.locator('.ant-tabs-tabpane-active')
    ev.candidateHeaders = await activePane.locator('.ant-table-thead th').allInnerTexts()
    ev.candidateRows = await activePane.locator('.ant-table-tbody tr').allInnerTexts()
    ev.contextHeaderCount = await page.locator('.ant-collapse-header').count()
    const body = await page.locator('body').innerText()
    for (const label of ['任务目标', '规划依据（上下文快照）', '步骤目标', '所需能力',
      '输入参数', '前置条件', '完成条件', '失败处理', '候选设备', '关键参数来源',
      '规划说明', '可执行步骤数', '剩余额度', '冻结时间']) {
      ev.visibleLabels[label] = body.includes(label)
    }
    ev.screenshot = 'TC-037-candidate-plan-task55.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await app.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-037-candidate-plan-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ route: ev.route, versionTabs: ev.versionTabs,
    candidateHeaders: ev.candidateHeaders, candidateRows: ev.candidateRows.length,
    visibleLabels: ev.visibleLabels }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
