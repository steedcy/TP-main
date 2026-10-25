// TC-020.S2: browser capability test result fields, restoring an existing enabled capability.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const line = fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .find(value => value.startsWith('|配置管理员|'))
const [, , username, password] = line.split('|')
const base = 'http://127.0.0.1:8080/api/v1'
const device = 'SIM_F2_DISPLAY'
const capability = 'CAP_INFO_DISPLAY'

async function main() {
  const login = await fetch(base + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }) })
  const token = (await login.json()).data.token
  const headers = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }
  const request = async (url, method = 'GET', body) => {
    const r = await fetch(base + url, { method, headers, body: body ? JSON.stringify(body) : undefined })
    return { status: r.status, body: await r.json() }
  }
  const capPath = `/devices/${device}/capabilities`
  const before = await request(capPath)
  const original = before.body.data.find(x => x.capabilityCode === capability)
  if (original.capabilityStatus !== 'ENABLED') throw Error('existing capability is not enabled')
  const result = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    deviceCode: device, capabilityCode: capability, beforeStatus: original.capabilityStatus }
  const browser = await chromium.launch({ executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(username)
    await page.locator('input[placeholder="密码"]').fill(password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    await page.goto('http://127.0.0.1:5173/devices/' + device + '/capabilities', { waitUntil: 'networkidle' })
    const row = page.locator('.ant-table-tbody .ant-table-row').filter({ hasText: capability }).first()
    await row.getByRole('button', { name: '模拟调用测试' }).click()
    const modal = page.locator('.ant-modal-content').filter({ hasText: '模拟调用测试结果' })
    await modal.waitFor({ state: 'visible' })
    result.modalLabels = await modal.locator('.ant-descriptions-item-label').allInnerTexts()
    result.modalValues = await modal.locator('.ant-descriptions-item-content').allInnerTexts()
    result.hasRequestPayload = result.modalLabels.some(x => x.includes('请求'))
    result.hasResponsePayload = result.modalLabels.some(x => x.includes('响应'))
    result.hasElapsedTime = result.modalLabels.some(x => x.includes('耗时'))
    await page.screenshot({ path: path.join(__dirname, 'evidence/TC-020-capability-test-modal.png') })
  } finally {
    await browser.close()
    const current = await request(capPath)
    result.afterTestStatus = current.body.data.find(x => x.capabilityCode === capability).capabilityStatus
    if (result.afterTestStatus === 'TESTED_PASSED') {
      const restored = await request(capPath + '/' + capability + '/status', 'POST', { status: 'ENABLED' })
      result.restoreHttpStatus = restored.status
    }
    const after = await request(capPath)
    result.afterRestoreStatus = after.body.data.find(x => x.capabilityCode === capability).capabilityStatus
    fs.writeFileSync(path.join(__dirname, 'evidence/TC-020-capability-test-modal.json'), JSON.stringify(result, null, 2) + '\n')
  }
  process.stdout.write(JSON.stringify(result) + '\n')
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1 })
