// TC-063.S2: capture the live operator detail, plan, assignment and timeline panels.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|运行操作员|'))
const [, , username, password] = line.split('|')
const id = Number(process.argv[2] || '19')
if (!Number.isInteger(id) || id <= 0) throw new Error('task id required')

async function main() {
  const browser = await chromium.launch({ executablePath:
    'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome', taskId: id }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto(`http://127.0.0.1:5173/tasks/${id}`, { waitUntil: 'networkidle' })
    ev.route = new URL(page.url()).pathname
    ev.header = await page.locator('.ant-descriptions').first().innerText()
    ev.cards = await page.locator('.ant-card').evaluateAll(cards => cards.map(card => ({
      title: card.querySelector('.ant-card-head-title')?.innerText || null,
      text: card.innerText
    })))
    ev.planTabs = await page.locator('.ant-tabs-tab').allInnerTexts()
    ev.timelineItemCount = await page.locator('.ant-timeline-item').count()
    ev.screenshot = `TC-063-task-detail-fields-task${id}.png`
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot), fullPage: true })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', `TC-063-task-detail-fields-task${id}.json`),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ taskId: id, cardTitles: ev.cards.map(x => x.title),
    timelineItemCount: ev.timelineItemCount, planTabs: ev.planTabs }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
