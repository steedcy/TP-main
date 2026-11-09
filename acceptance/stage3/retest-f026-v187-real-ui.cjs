const fs = require('fs');
const path = require('path');
const { chromium } = require('C:/Users/savy/Desktop/TIP-main/tip/.local-test/node_modules/playwright-core');

const root = path.resolve(__dirname, '../..');
const evidenceDir = path.join(__dirname, 'evidence');
const outFile = path.join(evidenceDir, 'SRS_F026-V1.187-real-ui-results.json');

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const results = {
    startedAt: new Date().toISOString(),
    tests: []
  };

  try {
    // 1. Login as OPERATOR (oprator / 12345678)
    console.log('Logging in as oprator (OPERATOR)...');
    await page.goto('http://127.0.0.1:15179/login', { waitUntil: 'networkidle' });
    await page.getByPlaceholder('账号').fill('oprator');
    await page.getByPlaceholder('密码').fill('12345678');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL('**/overview');

    // 2. Navigate to /tasks
    console.log('Navigating to /tasks...');
    await page.goto('http://127.0.0.1:15179/tasks', { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // 3. Open submit modal and test flight change form validations
    console.log('Opening task submission modal...');
    await page.getByRole('button', { name: '提交任务', exact: true }).click();
    await page.waitForTimeout(400);

    const modal = page.locator('.ant-modal');
    // Select task family: 航班变更应对
    console.log('Selecting task family: 航班变更应对...');
    await modal.locator('.ant-form-item').filter({ hasText: '任务族' }).locator('.ant-select').click();
    await page.waitForTimeout(300);
    await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option')
      .filter({ hasText: '航班变更应对' }).first().click();
    await page.waitForTimeout(300);

    // Check alert message and flight specific fields
    const alertText = await modal.locator('.ant-alert').innerText();
    const hasFlightAlert = alertText.includes('请使用虚构或脱敏航班信息') && alertText.includes('航延屏');

    // Test submit button disabled when fields are empty
    const okBtn = modal.locator('.ant-modal-footer button.ant-btn-primary');
    const initialDisabled = await okBtn.isDisabled();

    // Fill flightNumber
    await modal.locator('.ant-form-item').filter({ hasText: '航班号' }).locator('input').fill('CA1881');

    // Test change type selection: DELAY
    await modal.locator('.ant-form-item').filter({ hasText: '变更类型' }).locator('.ant-select').click();
    await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option')
      .filter({ hasText: '延误' }).first().click();
    await page.waitForTimeout(200);

    // Verify '变更后时间（必填）' is present
    const delayHasNewTimeRequired = await modal.locator('.ant-form-item').filter({ hasText: '变更后时间（必填）' }).count() > 0;

    // Switch change type to: GATE_CHANGE (登机口变更)
    await modal.locator('.ant-form-item').filter({ hasText: '变更类型' }).locator('.ant-select').click();
    await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option')
      .filter({ hasText: '登机口变更' }).first().click();
    await page.waitForTimeout(200);

    // Verify '变更后登机口（必填）' is present
    const gateHasNewGateRequired = await modal.locator('.ant-form-item').filter({ hasText: '变更后登机口（必填）' }).count() > 0;

    // Switch change type to: CANCEL (取消)
    await modal.locator('.ant-form-item').filter({ hasText: '变更类型' }).locator('.ant-select').click();
    await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option')
      .filter({ hasText: '取消' }).first().click();
    await page.waitForTimeout(200);

    // Verify '变更后时间' is hidden for CANCEL
    const cancelHidesNewTime = await modal.locator('.ant-form-item').filter({ hasText: '变更后时间' }).count() === 0;

    results.tests.push({
      name: 'ui-flight-change-conditional-fields-validation',
      hasFlightAlert,
      initialDisabled,
      delayHasNewTimeRequired,
      gateHasNewGateRequired,
      cancelHidesNewTime,
      result: (hasFlightAlert && initialDisabled && delayHasNewTimeRequired && gateHasNewGateRequired && cancelHidesNewTime) ? 'P' : 'F'
    });

    // 4. Fill valid GATE_CHANGE task and submit
    console.log('Filling valid GATE_CHANGE task form...');
    // Re-select GATE_CHANGE
    await modal.locator('.ant-form-item').filter({ hasText: '变更类型' }).locator('.ant-select').click();
    await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option')
      .filter({ hasText: '登机口变更' }).first().click();
    await page.waitForTimeout(200);

    // Set originalTime
    const origTimePicker = modal.locator('.ant-form-item').filter({ hasText: '原计划时间' }).locator('.ant-picker');
    await origTimePicker.click();
    await page.waitForTimeout(200);
    const nowBtn = page.locator('.ant-picker-dropdown:not(.ant-picker-dropdown-hidden) .ant-picker-now-btn');
    if (await nowBtn.count()) {
      await nowBtn.click();
    } else {
      await origTimePicker.locator('input').fill('2026-11-10 10:00:00');
      await page.keyboard.press('Enter');
    }
    await page.waitForTimeout(200);

    // Select originalGate: A01
    const origGateSelect = modal.locator('.ant-form-item').filter({ hasText: '原登机口' });
    await origGateSelect.locator('.ant-select').click();
    await page.waitForTimeout(300);
    const origDropdown = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').last();
    if (await origDropdown.locator('.ant-select-item-option:has-text("A01")').count()) {
      await origDropdown.locator('.ant-select-item-option:has-text("A01")').first().click();
    } else {
      await origGateSelect.locator('input').fill('A01');
      await page.keyboard.press('Enter');
    }
    await page.waitForTimeout(400);

    // Select newGate: B02
    const newGateSelect = modal.locator('.ant-form-item').filter({ hasText: '变更后登机口' });
    await newGateSelect.locator('.ant-select').click();
    await page.waitForTimeout(300);
    const newDropdown = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').last();
    if (await newDropdown.locator('.ant-select-item-option:has-text("B02")').count()) {
      await newDropdown.locator('.ant-select-item-option:has-text("B02")').first().click();
    } else {
      await newGateSelect.locator('input').fill('B02');
      await page.keyboard.press('Enter');
    }
    await page.waitForTimeout(400);

    // Fill changeDescription
    await modal.locator('.ant-form-item').filter({ hasText: '变更内容说明' }).locator('textarea')
      .fill('虚构航班CA1881因机位调整登机口变更至B02');
    await page.waitForTimeout(200);

    // Verify submit button is now enabled
    const readyToSubmit = !(await okBtn.isDisabled());
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F026-V1.187-ui-task-submission.png') });

    const [submitRes] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/v1/tasks') && r.request().method() === 'POST'),
      okBtn.click()
    ]);
    const submitJson = await submitRes.json();
    const createdId = submitJson.data?.id;
    console.log('Task submitted via UI, status:', submitRes.status(), 'ID:', createdId);

    results.tests.push({
      name: 'ui-flight-change-task-submission',
      readyToSubmit,
      httpStatus: submitRes.status(),
      createdTaskId: createdId,
      result: (readyToSubmit && submitRes.status() === 200 && !!createdId) ? 'P' : 'F'
    });

    // 5. Wait for execution and inspect task detail page
    console.log(`Waiting for execution and navigating to /tasks/${createdId}...`);
    await page.waitForTimeout(3000);
    await page.goto(`http://127.0.0.1:15179/tasks/${createdId}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Refresh if still executing
    for (let r = 0; r < 5; r++) {
      const statusText = await page.locator('body').innerText();
      if (statusText.includes('已完成') || statusText.includes('执行中') || statusText.includes('待人工处理')) {
        break;
      }
      await page.waitForTimeout(1000);
      await page.reload({ waitUntil: 'networkidle' });
    }

    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F026-V1.187-ui-flight-channel-card.png'), fullPage: true });

    const pageText = await page.locator('body').innerText();
    const hasChannelCardTitle = pageText.includes('航班变更渠道响应');
    const hasBoardChannel = pageText.includes('航延屏');
    const hasDisplayChannel = pageText.includes('智慧航显');
    const hasRobotChannel = pageText.includes('机器人');

    const detailPassed = hasChannelCardTitle && hasBoardChannel && hasDisplayChannel && hasRobotChannel;
    results.tests.push({
      name: 'ui-flight-change-channel-card-render',
      taskId: createdId,
      hasChannelCardTitle,
      hasBoardChannel,
      hasDisplayChannel,
      hasRobotChannel,
      result: detailPassed ? 'P' : 'F'
    });
    console.log('Flight change channel response card UI test result:', detailPassed ? 'P' : 'F');

  } catch (err) {
    console.error('UI Test Error:', err);
    results.error = String(err);
  } finally {
    results.endedAt = new Date().toISOString();
    fs.writeFileSync(outFile, JSON.stringify(results, null, 2), 'utf8');
    await browser.close();
    console.log('Finished real UI test execution, saved to:', outFile);
  }
})();
