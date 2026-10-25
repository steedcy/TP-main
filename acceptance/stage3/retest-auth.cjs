// Live V1.5 browser retest of TC-001.S1-S3. Never writes passwords or tokens.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')

const root = path.resolve(__dirname, '../..')
const outdir = path.join(__dirname, 'evidence')
const origin = 'http://127.0.0.1:5173'
const api = 'http://127.0.0.1:8080/api/v1'
const browserPath = process.env.CHROME_EXE || 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe'
const accounts = Object.fromEntries(fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .filter(line => /^\|(?:系统管理员|运行操作员|配置管理员)\|/.test(line))
  .map(line => { const [role, username, password] = line.slice(1).split('|'); return [role, { username, password }] }))

async function main() {
  fs.mkdirSync(outdir, { recursive: true })
  const browser = await chromium.launch({ executablePath: browserPath, headless: true })
  const evidence = { observedAt: new Date().toISOString(), gitHead: '0d798ceb53bc37498f353b4796f2081b92e2011b',
    browser: 'Chrome', viewport: '1366x768', checks: {}, roles: [] }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto(origin + '/login', { waitUntil: 'networkidle' })
    let calls = 0
    page.on('request', request => { if (request.url().endsWith('/api/v1/auth/login')) calls++ })
    const username = page.locator('input[placeholder="账号"]')
    const password = page.locator('input[placeholder="密码"]')
    const submit = page.locator('button[type="submit"]')
    evidence.checks.initialEmpty = (await username.inputValue() === '' && await password.inputValue() === '')
    evidence.checks.passwordType = await password.getAttribute('type')
    evidence.checks.passwordRevealControls = await page.locator('.ant-input-password-icon').count()
    await submit.click()
    await page.getByText('请输入账号').waitFor({ state: 'visible', timeout: 3000 }).catch(() => {})
    await page.getByText('请输入密码').waitFor({ state: 'visible', timeout: 3000 }).catch(() => {})
    evidence.checks.emptyAccountMessage = await page.getByText('请输入账号').isVisible()
    evidence.checks.emptyPasswordMessage = await page.getByText('请输入密码').isVisible()
    evidence.checks.emptyAuthCalls = calls
    await page.screenshot({ path: path.join(outdir, 'TC-001-S1-empty.png') })
    await username.fill('u'.repeat(33))
    evidence.checks.usernameOverMaxStoredLength = (await username.inputValue()).length
    await password.fill('p'.repeat(33))
    evidence.checks.passwordOverMaxStoredLength = (await password.inputValue()).length
    await username.fill('u')
    await password.fill('short7!')
    await submit.click()
    evidence.checks.shortPasswordRejected = await page.getByText('密码长度为8～32位').isVisible()
    evidence.checks.callsAfterShortPassword = calls
    // Account-length edges submit to authentication but must not establish a session.
    for (const n of [1, 32]) {
      await username.fill('u'.repeat(n))
      await password.fill('invalid8')
      const before = calls
      await submit.click()
      await page.waitForTimeout(500)
      evidence.checks['usernameLength' + n + 'Submitted'] = calls === before + 1
    }
    await username.fill('u'.repeat(18))
    for (const n of [8, 32]) {
      await password.fill('p'.repeat(n))
      const before = calls
      await submit.click()
      await page.waitForTimeout(500)
      evidence.checks['passwordLength' + n + 'Submitted'] = calls === before + 1
    }
    await page.screenshot({ path: path.join(outdir, 'TC-001-S1-boundaries.png') })
    await page.close()

    for (const [role, credential] of Object.entries(accounts)) {
      const context = await browser.newContext({ viewport: { width: 1366, height: 768 } })
      const rolePage = await context.newPage()
      await rolePage.goto(origin + '/login', { waitUntil: 'networkidle' })
      await rolePage.locator('input[placeholder="账号"]').fill(credential.username)
      await rolePage.locator('input[placeholder="密码"]').fill(credential.password)
      await rolePage.locator('button[type="submit"]').click()
      await rolePage.waitForURL('**/overview', { timeout: 8000 })
      const heading = await rolePage.locator('.ant-layout-header > span').innerText()
      const token = await rolePage.evaluate(() => {
        const values = Object.entries(localStorage)
        return values.find(([key]) => key.toLowerCase().includes('token'))?.[1] || ''
      })
      await rolePage.screenshot({ path: path.join(outdir, `TC-001-S2-${credential.username}.png`) })
      await rolePage.getByRole('button', { name: '退出登录' }).click()
      await rolePage.waitForURL('**/login', { timeout: 8000 })
      await rolePage.goto(origin + '/overview')
      await rolePage.waitForURL('**/login', { timeout: 8000 })
      const postLogout = await fetch(api + '/tasks?page=1&size=1', { headers: { Authorization: 'Bearer ' + token } })
      evidence.roles.push({ role, username: credential.username, headerShowsRole: heading.includes(role),
        overviewLoaded: true, returnedToLogin: true, protectedRouteRedirected: true,
        formerTokenHttpStatus: postLogout.status })
      await context.close()
    }
    const admin = accounts['系统管理员']
    const login = await fetch(api + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(admin) })
    const session = (await login.json()).data
    const logs = await fetch(api + '/operation-logs?page=1&size=100', { headers: { Authorization: 'Bearer ' + session.token } })
    const recent = (await logs.json()).data.content.filter(row =>
      accounts[row.username && Object.keys(accounts).find(role => accounts[role].username === row.username)] &&
      ['LOGIN', 'LOGOUT'].includes(row.operationType))
    evidence.checks.recentAuthLogCount = recent.length
    evidence.checks.authLogsHaveIdentityTimeIpResult = recent.length >= 6 && recent.every(row =>
      row.username && (row.operationTime || row.createdAt) && row.sourceIp && row.operationResult)
    evidence.checks.authLogsContainPassword = recent.some(row =>
      Object.values(accounts).some(account => JSON.stringify(row).includes(account.password)))
    await fetch(api + '/auth/logout', { method: 'POST', headers: { Authorization: 'Bearer ' + session.token } })
  } finally { await browser.close() }
  evidence.results = {
    'TC-001.S1': Object.entries(evidence.checks).every(([key, value]) =>
      key === 'passwordType' ? value === 'password' :
      key === 'passwordRevealControls' || key === 'emptyAuthCalls' || key === 'callsAfterShortPassword' ? value === 0 :
      key.endsWith('StoredLength') ? value === 32 :
      key.startsWith('recentAuth') || key.startsWith('authLogs') ? true : value === true),
    'TC-001.S2': evidence.roles.length === 3 && evidence.roles.every(row =>
      row.headerShowsRole && row.overviewLoaded && row.returnedToLogin && row.protectedRouteRedirected && row.formerTokenHttpStatus === 401),
    'TC-001.S3': evidence.checks.authLogsHaveIdentityTimeIpResult && !evidence.checks.authLogsContainPassword,
  }
  fs.writeFileSync(path.join(outdir, 'TC-001-auth.json'), JSON.stringify(evidence, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ results: evidence.results, checks: evidence.checks, roles: evidence.roles }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
