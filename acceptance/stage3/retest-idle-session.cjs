// TC-087: real 31-minute idle browser session. No token or password is persisted.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|系统管理员|'))
const [, , username, password] = line.split('|')
const out = path.join(__dirname, 'evidence', 'TC-087-idle-session.json')
const save = value => fs.writeFileSync(out, JSON.stringify(value, null, 2) + '\n')
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
async function main() {
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const evidence = { startedAt: new Date().toISOString(), runtimeInput: 'V1.5', browser: 'Chrome',
    viewport: '1366x768', status: 'RUNNING' }
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/operation-logs', { waitUntil: 'networkidle' })
    const oldToken = await page.evaluate(() => localStorage.getItem('token'))
    let apiRequestsDuringIdle = 0
    const idleStarted = Date.now()
    page.on('request', req => { if (req.url().includes('/api/v1/')) apiRequestsDuringIdle++ })
    evidence.idleStartedAt = new Date(idleStarted).toISOString()
    evidence.expectedCheckAt = new Date(idleStarted + 31 * 60 * 1000).toISOString()
    save(evidence)
    await pause(31 * 60 * 1000)
    evidence.idleElapsedMs = Date.now() - idleStarted
    evidence.apiRequestsDuringIdle = apiRequestsDuringIdle
    const response = page.waitForResponse(res => res.url().includes('/api/v1/operation-logs'))
    await page.locator('button').filter({ hasText: /查\s*询/ }).click()
    evidence.expiredHttpStatus = (await response).status()
    await page.waitForURL('**/login', { timeout: 10000 })
    evidence.redirectedToLogin = true
    evidence.expiryPromptShown = await page.getByText('登录已过期，请重新登录').first().isVisible()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-087-expired.png') })
    evidence.oldTokenAfterExpiryStatus = (await fetch('http://127.0.0.1:8080/api/v1/operation-logs',
      { headers: { Authorization: 'Bearer ' + oldToken } })).status
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    evidence.reauthenticated = true
    const freshToken = await page.evaluate(() => localStorage.getItem('token'))
    evidence.newTokenWorks = (await fetch('http://127.0.0.1:8080/api/v1/operation-logs',
      { headers: { Authorization: 'Bearer ' + freshToken } })).status === 200
    evidence.oldTokenStillInvalid = (await fetch('http://127.0.0.1:8080/api/v1/operation-logs',
      { headers: { Authorization: 'Bearer ' + oldToken } })).status === 401
    evidence.status = evidence.idleElapsedMs >= 31 * 60 * 1000 && evidence.apiRequestsDuringIdle === 0
      && evidence.expiredHttpStatus === 401 && evidence.redirectedToLogin && evidence.expiryPromptShown
      && evidence.oldTokenAfterExpiryStatus === 401 && evidence.reauthenticated
      && evidence.newTokenWorks && evidence.oldTokenStillInvalid ? 'PASS' : 'FAIL'
    evidence.finishedAt = new Date().toISOString()
    await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-087-after-relogin.png') })
  } catch (error) {
    evidence.status = 'ERROR'
    evidence.error = String(error)
    evidence.finishedAt = new Date().toISOString()
  } finally {
    save(evidence)
    await browser.close()
  }
  process.stdout.write(JSON.stringify({ status: evidence.status, evidence: out }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
