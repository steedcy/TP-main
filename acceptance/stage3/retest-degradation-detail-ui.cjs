// TC-048.S2: inspect actual baseline downgrade details and original goal in Chrome.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const account = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(line => line.startsWith('|运行操作员|'))
const [, , username, password] = account.split('|')

async function main() {
  const browser = await chromium.launch({ executablePath:
    'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const observedAt = new Date().toISOString()
  const stamp = observedAt.replace(/[-:.]/g, '').replace(/\d{3}Z$/, 'Z')
  const evidence = { observedAt, runtimeInput: 'V1.5', browser: 'Chrome', tasks: [] }
  try {
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    for (const id of [19, 83]) {
      await page.goto(`http://127.0.0.1:5173/tasks/${id}`, { waitUntil: 'networkidle' })
      const card = page.locator('.ant-card').filter({ has: page.getByText('计划版本与校验/判定结果', { exact: true }) })
      const item = {
        taskId: id,
        url: page.url(),
        header: await page.locator('.ant-descriptions').first().innerText(),
        tabs: await card.locator('.ant-tabs-tab').allInnerTexts(),
        planCardLinks: await card.locator('a').evaluateAll(links => links.map(a =>
          ({ text: a.innerText, href: a.getAttribute('href') }))),
        versions: []
      }
      for (const tab of item.tabs) {
        await card.getByText(tab, { exact: true }).click()
        item.versions.push({ tab, detail: await card.locator('.ant-tabs-tabpane-active').innerText() })
      }
      item.screenshot = `TC-048-downgrade-task${id}-${stamp}.png`
      await page.screenshot({ path: path.join(__dirname, 'evidence', item.screenshot), fullPage: true })
      evidence.tasks.push(item)
    }
  } finally {
    await browser.close()
  }
  const name = `TC-048-downgrade-detail-ui-${stamp}.json`
  fs.writeFileSync(path.join(__dirname, 'evidence', name), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ evidence: name,
    tasks: evidence.tasks.map(x => ({ id: x.taskId, tabs: x.tabs, planCardLinks: x.planCardLinks })) }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
