// F020.R07: read a completed task's timeline through the operator UI.
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
    browser: 'Chrome', taskId: 19 }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/tasks/19', { waitUntil: 'networkidle' })
    await page.locator('.ant-timeline-item').first().waitFor({ state: 'visible' })
    ev.route = new URL(page.url()).pathname
    const timelineCard = page.locator('.ant-card').filter({ has: page.locator('.ant-timeline') }).first()
    ev.cardTitle = await timelineCard.locator('.ant-card-head-title').innerText()
    ev.items = await timelineCard.locator('.ant-timeline-item').allInnerTexts()
    ev.editControls = await timelineCard.getByRole('button', { name: /编辑|修改|删除/ }).count()
    ev.editableElements = await timelineCard.locator('[contenteditable="true"],input,textarea').count()
    ev.screenshot = 'SRS_F020-R07-timeline-task19.png'
    await timelineCard.screenshot({ path: path.join(__dirname, 'evidence', ev.screenshot) })
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'SRS_F020-R07-timeline-task19.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ route: ev.route, cardTitle: ev.cardTitle,
    count: ev.items.length, editControls: ev.editControls,
    editableElements: ev.editableElements }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
