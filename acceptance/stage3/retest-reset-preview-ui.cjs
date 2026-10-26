// TC-006.S1: inspect preview, confirmation guards and cancel without resetting data.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core')
const root = path.resolve(__dirname, '../..')
const accounts = Object.fromEntries(fs.readFileSync(path.join(root, 'user.md'), 'utf8').split(/\r?\n/)
  .filter(line => /^\|(?:系统管理员|运行操作员|配置管理员)\|/.test(line))
  .map(line => { const [, role, username, password] = line.split('|'); return [role, { username, password }] }))
const api = 'http://127.0.0.1:8080/api/v1'

async function auth(role) {
  const response = await fetch(api + '/auth/login', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(accounts[role]) })
  return (await response.json()).data.token
}

async function preview(token) {
  const response = await fetch(api + '/demo-data/reset-preview', {
    headers: { Authorization: 'Bearer ' + token } })
  return { status: response.status, body: await response.json() }
}

async function main() {
  const admin = await auth('系统管理员')
  const config = await auth('配置管理员')
  const operator = await auth('运行操作员')
  const before = await preview(admin)
  const configDenied = await preview(config)
  const operatorDenied = await preview(operator)
  const v = before.body.data
  const ev = { observedAt: new Date().toISOString(), runtimeInput: 'V1.5',
    isolatedSchema: 'tip_stage2_v14', browser: 'Chrome', viewport: '1366x768',
    adminPreviewHttpStatus: before.status, configPreviewHttpStatus: configDenied.status,
    operatorPreviewHttpStatus: operatorDenied.status,
    preview: { enabled: v.enabled, version: v.version, generatedAt: v.generatedAt,
      sourceDigest: v.sourceDigest, currentContentDigest: v.currentContentDigest,
      impactScope: v.impactScope, preservedScope: v.preservedScope,
      postResetState: v.postResetState, blockingTasks: v.blockingTasks,
      busyDemoAgents: v.busyDemoAgents, confirmationPhraseLength: v.confirmationPhrase.length } }
  const browser = await chromium.launch({
    executablePath: 'C:\\Users\\savy\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  })
  try {
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
    await page.locator('input[placeholder="账号"]').fill(accounts['系统管理员'].username)
    await page.locator('input[placeholder="密码"]').fill(accounts['系统管理员'].password)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('**/overview')
    ev.adminMenuVisible = await page.getByText('标准演示数据复位').isVisible()
    let resetPosts = 0
    page.on('request', request => {
      if (request.url().endsWith('/demo-data/reset') && request.method() === 'POST') resetPosts++
    })
    await page.goto('http://127.0.0.1:5173/demo-data-reset', { waitUntil: 'networkidle' })
    const card = page.locator('.ant-card').first()
    await card.getByText('数据集版本').waitFor({ state: 'visible' })
    ev.visibleFields = ['数据集版本', '生成时间', '源数据 SHA-256', '当前业务数据摘要',
      '影响范围', '保留范围', '复位后状态']
    const body = await card.innerText()
    ev.visibleFields = ev.visibleFields.filter(label => body.includes(label))
    ev.confirmationPhraseShown = body.includes(v.confirmationPhrase)
    const input = card.locator('input[type="text"]').last()
    const checkbox = card.locator('.ant-checkbox-input')
    const resetButton = card.getByRole('button', { name: '恢复标准演示数据' })
    ev.emptyPhraseButtonDisabled = await resetButton.isDisabled()
    await input.fill('S3_WRONG_PHRASE')
    await checkbox.check()
    ev.wrongPhraseButtonDisabled = await resetButton.isDisabled()
    await input.fill(v.confirmationPhrase)
    ev.correctPhraseWithAcknowledgementEnabled = await resetButton.isEnabled()
    await resetButton.click()
    const modal = page.locator('.ant-modal-confirm')
    await modal.waitFor({ state: 'visible' })
    ev.confirmationTitle = await modal.innerText()
    ev.confirmationScreenshot = 'TC-006-reset-confirm-cancel.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.confirmationScreenshot), fullPage: true })
    await modal.locator('.ant-modal-confirm-btns button').first().click()
    await modal.waitFor({ state: 'hidden' })
    ev.modalClosedAfterCancel = true
    ev.resetPostCount = resetPosts
    ev.cancelScreenshot = 'TC-006-reset-canceled.png'
    await page.screenshot({ path: path.join(__dirname, 'evidence', ev.cancelScreenshot), fullPage: true })
  } finally { await browser.close() }
  const after = await preview(admin)
  ev.afterPreviewHttpStatus = after.status
  ev.afterVersion = after.body.data.version
  ev.afterSourceDigest = after.body.data.sourceDigest
  ev.afterContentDigest = after.body.data.currentContentDigest
  fs.writeFileSync(path.join(__dirname, 'evidence', 'TC-006-reset-preview-ui.json'),
    JSON.stringify(ev, null, 2) + '\n')
  process.stdout.write(JSON.stringify({ adminPreviewHttpStatus: ev.adminPreviewHttpStatus,
    configPreviewHttpStatus: ev.configPreviewHttpStatus,
    operatorPreviewHttpStatus: ev.operatorPreviewHttpStatus,
    visibleFields: ev.visibleFields.length, emptyDisabled: ev.emptyPhraseButtonDisabled,
    wrongDisabled: ev.wrongPhraseButtonDisabled, cancelClosed: ev.modalClosedAfterCancel,
    resetPostCount: ev.resetPostCount, digestUnchanged: ev.afterContentDigest === ev.preview.currentContentDigest }) + '\n')
}
main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
