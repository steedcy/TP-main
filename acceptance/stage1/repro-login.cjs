const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')

const base = process.env.STAGE1_WEB_URL || 'http://127.0.0.1:5173'
const chrome = process.env.CHROME_EXE || 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe'
const out = path.join(__dirname, 'evidence', 'login-directed.json')

async function main() {
  const browser = await chromium.launch({ executablePath: chrome, headless: true })
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
  const evidence = { observedAt: new Date().toISOString(), url: base, checks: {} }
  try {
    await page.goto(`${base}/login`, { waitUntil: 'networkidle' })
    let authenticationRequests = 0
    page.on('request', request => {
      if (request.url().includes('/api/v1/auth/login')) authenticationRequests++
    })
    await page.locator('button[type=submit]').click()
    await page.getByText('请输入账号').waitFor({ state: 'visible', timeout: 2000 }).catch(() => {})
    await page.getByText('请输入密码').waitFor({ state: 'visible', timeout: 2000 }).catch(() => {})
    evidence.checks.emptyAccountMessage = await page.getByText('请输入账号').isVisible()
    evidence.checks.emptyPasswordMessage = await page.getByText('请输入密码').isVisible()
    evidence.checks.emptyAuthRequests = authenticationRequests
    evidence.checks.passwordInputType = await page.locator('input[placeholder="密码"]').getAttribute('type')
    evidence.checks.visibilityToggleCount = await page.locator('.ant-input-password-icon').count()
    fs.mkdirSync(path.dirname(out), { recursive: true })
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'login-empty.png') })

    await page.locator('input[placeholder="账号"]').fill('stage1-no-such-user')
    await page.locator('input[placeholder="密码"]').fill('fictional-password-123')
    await page.route('**/api/v1/auth/login', async route => route.fulfill({
      status: 403, contentType: 'application/json', body: JSON.stringify({ code: 2005, message: '无权限访问' })
    }))
    await page.locator('button[type=submit]').click()
    await page.getByText('账号或密码错误').waitFor({ state: 'visible', timeout: 2000 }).catch(() => {})
    evidence.checks.lockedOrInactiveUnifiedMessage = await page.getByText('账号或密码错误').isVisible()
    evidence.checks.incorrectPermissionMessageShown = await page.getByText('无权限访问，该操作需要更高权限角色').count()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'login-unified.png') })
    fs.writeFileSync(out, JSON.stringify(evidence, null, 2) + '\n')
    const checks = evidence.checks
    if (!checks.emptyAccountMessage || !checks.emptyPasswordMessage || checks.emptyAuthRequests !== 0
        || checks.passwordInputType !== 'password' || checks.visibilityToggleCount !== 0
        || !checks.lockedOrInactiveUnifiedMessage || checks.incorrectPermissionMessageShown !== 0) {
      throw new Error(`login directed check failed: ${JSON.stringify(checks)}`)
    }
    process.stdout.write(JSON.stringify(evidence) + '\n')
  } finally {
    await browser.close()
  }
}

main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
