// TC-090 partial live browser/resolution smoke of core pages and task/config modals.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const accounts = Object.fromEntries(fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .filter(line => /^\|(?:运行操作员|配置管理员)\|/.test(line))
  .map(line => { const [, role, username, password] = line.split('|'); return [role, { username, password }] }))
const browsers = [
  { name: 'Chrome', executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe' },
  { name: 'Edge', executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' }
]

async function login(page, role) {
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
  await page.locator('input[placeholder="账号"]').fill(accounts[role].username)
  await page.locator('input[placeholder="密码"]').fill(accounts[role].password)
  await page.locator('button[type="submit"]').click()
  await page.waitForURL('**/overview')
}
async function measure(page, label) {
  const size = await page.evaluate(() => ({ viewportWidth: window.innerWidth,
    bodyScrollWidth: document.body.scrollWidth, documentScrollWidth: document.documentElement.scrollWidth }))
  return { label, route: new URL(page.url()).pathname, ...size, horizontalOverflow: Math.max(size.bodyScrollWidth, size.documentScrollWidth) > size.viewportWidth }
}

async function main() {
  const evidence = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5', browserVersions: {}, samples: [] }
  for (const config of browsers) {
    const browser = await chromium.launch({ executablePath: config.executablePath, headless: true })
    evidence.browserVersions[config.name] = browser.version()
    try {
      for (const [width, height] of [[1366, 768], [1920, 1080]]) {
        const context = await browser.newContext({ viewport: { width, height } })
        const page = await context.newPage()
        await login(page, '配置管理员')
        await page.goto('http://127.0.0.1:5173/devices', { waitUntil: 'networkidle' })
        evidence.samples.push({ browser: config.name, resolution: `${width}x${height}`, ...await measure(page, 'devices') })
        await page.getByRole('button', { name: '新增设备' }).click()
        await page.waitForTimeout(450)
        evidence.samples.push({ browser: config.name, resolution: `${width}x${height}`, ...await measure(page, 'device-modal') })
        if (width === 1366) await page.screenshot({ path: path.join(__dirname, 'evidence', `TC-090-${config.name}-device-modal.png`) })
        await context.close()
        const opContext = await browser.newContext({ viewport: { width, height } })
        const op = await opContext.newPage()
        await login(op, '运行操作员')
        for (const [route, label] of [['tasks', 'tasks'], ['situation', 'situation'], ['task-trace', 'trace']]) {
          await op.goto(`http://127.0.0.1:5173/${route}`, { waitUntil: 'networkidle' })
          evidence.samples.push({ browser: config.name, resolution: `${width}x${height}`, ...await measure(op, label) })
          if (route === 'tasks') {
            await op.getByRole('button', { name: '提交任务' }).click()
            await op.waitForTimeout(450)
            evidence.samples.push({ browser: config.name, resolution: `${width}x${height}`, ...await measure(op, 'task-modal') })
            if (width === 1366) await op.screenshot({ path: path.join(__dirname, 'evidence', `TC-090-${config.name}-task-modal.png`) })
          }
        }
        await opContext.close()
      }
    } finally { await browser.close() }
  }
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-090-browser-layout.json'), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ samples: evidence.samples.length, overflow: evidence.samples.filter(x => x.horizontalOverflow) }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
