// TC-064.S1: compare pending-manual emphasis and action area with a completed task.
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
    browser: 'Chrome', viewport: '1366x768' }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.waitForFunction(() => {
      const card = [...document.querySelectorAll('.ant-card')]
        .find(element => element.innerText.includes('待人工任务数'))
      return card && !card.innerText.includes('--')
    })
    const card = page.locator('.ant-card').filter({ hasText: '待人工任务数' }).first()
    ev.overview = { route: new URL(page.url()).pathname,
      pendingCardText: await card.innerText(),
      borderColor: await card.evaluate(el => getComputedStyle(el).borderColor),
      screenshot: 'TC-064-pending-overview.png' }
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.overview.screenshot), fullPage: true })

    await page.goto('http://127.0.0.1:5173/tasks?status=PENDING_MANUAL', { waitUntil: 'networkidle' })
    const pending = page.locator('.ant-table-row').filter({ hasText: 'TASK-20261025-0020' })
    await pending.waitFor({ state: 'visible' })
    ev.pendingList = { route: new URL(page.url()).pathname,
      rowText: await pending.innerText(),
      rowClass: await pending.getAttribute('class'),
      rowBackground: await pending.evaluate(el => getComputedStyle(el).backgroundColor),
      tagClass: await pending.locator('.ant-tag').getAttribute('class'),
      tagColor: await pending.locator('.ant-tag').evaluate(el => getComputedStyle(el).color),
      tagBackground: await pending.locator('.ant-tag').evaluate(el => getComputedStyle(el).backgroundColor),
      screenshot: 'TC-064-pending-list.png' }
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.pendingList.screenshot), fullPage: true })

    await page.goto('http://127.0.0.1:5173/tasks?status=COMPLETED', { waitUntil: 'networkidle' })
    const completed = page.locator('.ant-table-row').filter({ hasText: 'TASK-20261026-0059' })
    await completed.waitFor({ state: 'visible' })
    ev.completedList = { rowText: await completed.innerText(),
      rowClass: await completed.getAttribute('class'),
      rowBackground: await completed.evaluate(el => getComputedStyle(el).backgroundColor),
      tagClass: await completed.locator('.ant-tag').getAttribute('class'),
      tagColor: await completed.locator('.ant-tag').evaluate(el => getComputedStyle(el).color),
      tagBackground: await completed.locator('.ant-tag').evaluate(el => getComputedStyle(el).backgroundColor) }

    await page.goto('http://127.0.0.1:5173/tasks/20', { waitUntil: 'networkidle' })
    ev.pendingDetail = { route: new URL(page.url()).pathname,
      manualCardCount: await page.locator('.ant-card').filter({ hasText: '待人工处理' }).count(),
      actions: Object.fromEntries(await Promise.all(
        ['转基线执行', '重试规划', '置为失败', '终止任务'].map(async name =>
          [name, await page.getByRole('button', { name }).count()]))),
      screenshot: 'TC-064-pending-detail.png' }
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.pendingDetail.screenshot), fullPage: true })

    await page.goto('http://127.0.0.1:5173/tasks/19', { waitUntil: 'networkidle' })
    ev.completedDetail = { route: new URL(page.url()).pathname,
      actions: Object.fromEntries(await Promise.all(
        ['转基线执行', '重试规划', '置为失败', '终止任务'].map(async name =>
          [name, await page.getByRole('button', { name }).count()]))) }
  } finally { await browser.close() }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-064-pending-manual-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ overview: ev.overview, pendingList: {
    rowClass: ev.pendingList.rowClass, rowBackground: ev.pendingList.rowBackground,
    tagClass: ev.pendingList.tagClass, tagColor: ev.pendingList.tagColor,
    tagBackground: ev.pendingList.tagBackground },
    completedList: { rowClass: ev.completedList.rowClass,
      rowBackground: ev.completedList.rowBackground, tagClass: ev.completedList.tagClass,
      tagColor: ev.completedList.tagColor, tagBackground: ev.completedList.tagBackground },
    pendingDetail: ev.pendingDetail.actions, completedDetail: ev.completedDetail.actions }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
