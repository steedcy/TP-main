// TC-041.S1: inspect the live task 94 validation error list in Chrome.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const taskId = Number(process.env.STAGE3_TASK_ID || 94)
const name = 'TC-041-plan-ui-task' + taskId + '-' + new Date().toISOString().replace(/[-:]/g, '').replace(/\..*/, 'Z')

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    browser: 'Chrome', taskId, route: null, tabs: [], candidateDetail: '',
    baselineDetail: '', pageStatus: '', screenshot: name + '.png' }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview', { timeout: 10000 })
    await page.goto('http://127.0.0.1:5173/tasks/' + taskId, { waitUntil: 'networkidle' })
    await page.getByText('计划版本与校验/判定结果').waitFor({ state: 'visible', timeout: 10000 })
    ev.route = new URL(page.url()).pathname
    ev.pageStatus = (await page.locator('body').innerText()).slice(0, 2200)
    const plan = page.locator('.ant-card').filter({ hasText: '计划版本与校验/判定结果' }).first()
    ev.tabs = await plan.locator('.ant-tabs-tab').allInnerTexts()
    const count = await plan.locator('.ant-tabs-tab').count()
    for (let i = 0; i < count; i++) {
      await plan.locator('.ant-tabs-tab').nth(i).click()
      const detail = await plan.locator('.ant-tabs-tabpane-active').innerText()
      if (ev.tabs[i].includes('自主规划')) ev.candidateDetail = detail
      if (ev.tabs[i].includes('基线模板')) ev.baselineDetail = detail
    }
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', name + '.json'), JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ evidence: name + '.json', route: ev.route,
    tabs: ev.tabs, noCandidateErrorVisible: ev.candidateDetail.includes('ERR_NO_ONLINE_CANDIDATE'),
    errors: (ev.candidateDetail.match(/ERR_NO_ONLINE_CANDIDATE/g) || []).length }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
