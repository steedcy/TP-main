// UI part of TC-002.S1-S2. Temporary users are disabled after observation.
const fs = require('node:fs')
const path = require('node:path')
const crypto = require('node:crypto')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const accountLine = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(line => line.startsWith('|系统管理员|'))
const [, , , adminPassword] = accountLine.split('|')
const api = 'http://127.0.0.1:8080/api/v1'
const origin = 'http://127.0.0.1:5173'
const stamp = Date.now().toString(36)
const password = 'T3!' + crypto.randomBytes(12).toString('hex')
const wrong = 'w3!' + crypto.randomBytes(12).toString('hex')
const names = { A: 's3uia' + stamp, B: 's3uib' + stamp, C: 's3uic' + stamp }
let token
async function call(route, method = 'GET', data) {
  const response = await fetch(api + route, { method,
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
    body: data === undefined ? undefined : JSON.stringify(data) })
  const body = await response.json()
  if (!response.ok || body.code !== 200) throw Error(`${method} ${route}: HTTP ${response.status}, code ${body.code}`)
  return body.data
}
async function main() {
  const admin = await fetch(api + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: adminPassword }) })
  token = (await admin.json()).data.token
  const ids = {}
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  const observed = { at: new Date().toISOString(), gitHead: '0d798ceb53bc37498f353b4796f2081b92e2011b',
    browser: 'Chrome', viewport: '1366x768', accounts: names, attempts: [] }
  try {
    for (const [key, name] of Object.entries(names)) {
      ids[key] = (await call('/users', 'POST', { username: name, password, realName: 'Stage 3 UI ' + key,
        role: 'OPERATOR', contact: '00000000000' })).id
    }
    await call('/users/' + ids.C + '/status', 'POST', { status: 'INACTIVE' })
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    async function attempt(label, username, guess) {
      await page.goto(origin + '/login', { waitUntil: 'networkidle' })
      await page.locator('input[placeholder="账号"]').fill(username)
      await page.locator('input[placeholder="密码"]').fill(guess)
      await page.locator('button[type="submit"]').click()
      await page.getByText('账号或密码错误').first().waitFor({ state: 'visible', timeout: 6000 }).catch(() => {})
      const result = { label, unifiedPrompt: await page.getByText('账号或密码错误').first().isVisible(),
        stayedOnLogin: new URL(page.url()).pathname === '/login',
        noSessionToken: await page.evaluate(() => !localStorage.getItem('token')) }
      observed.attempts.push(result)
      await page.screenshot({ path: path.join(__dirname, 'evidence', 'TC-002-' + label + '.png') })
    }
    await attempt('unknown', 's3missing' + stamp, wrong)
    await attempt('inactive', names.C, password)
    await attempt('b-wrong', names.B, wrong)
    for (let n = 1; n <= 3; n++) await attempt('a-wrong-' + n, names.A, wrong)
    await attempt('a-locked-correct', names.A, password)
    observed.pass = observed.attempts.length === 7 && observed.attempts.every(a =>
      a.unifiedPrompt && a.stayedOnLogin && a.noSessionToken)
  } catch (error) {
    observed.error = String(error)
  } finally {
    for (const [key, id] of Object.entries(ids)) {
      const row = (await call('/users?page=1&size=100')).content.find(row => row.id === id)
      if (row?.status === 'LOCKED') await call('/users/' + id + '/unlock', 'POST')
      if (row?.status !== 'INACTIVE') await call('/users/' + id + '/status', 'POST', { status: 'INACTIVE' })
    }
    await browser.close()
    fs.mkdirSync(path.join(__dirname, 'evidence'), { recursive: true })
    fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-002-login-ui.json'), JSON.stringify(observed, null, 2) + '\n')
  }
  if (observed.error) throw Error(observed.error)
  process.stdout.write(JSON.stringify({ pass: observed.pass, attempts: observed.attempts }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
