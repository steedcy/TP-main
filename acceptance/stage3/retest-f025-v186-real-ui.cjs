const fs = require('fs');
const path = require('path');
const { chromium } = require('C:/Users/savy/Desktop/TIP-main/tip/.local-test/node_modules/playwright-core');

const root = path.resolve(__dirname, '../..');
const evidenceDir = path.join(__dirname, 'evidence');
const outFile = path.join(evidenceDir, 'SRS_F025-V1.186-real-ui-results.json');

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

    // 3. Submit special passenger goal requiring clarification
    console.log('Opening task submission modal...');
    await page.getByRole('button', { name: '提交任务', exact: true }).click();
    await page.waitForTimeout(400);

    const goalText = 'F186_UI_SPECIAL_PASSENGER 为轮椅旅客提供协助前往服务点';
    await page.locator('textarea').fill(goalText);
    await page.waitForTimeout(200);
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F025-V1.186-ui-task-submission.png') });

    const [submitRes] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/v1/tasks') && r.request().method() === 'POST'),
      page.locator('.ant-modal-footer button.ant-btn-primary').click()
    ]);
    const submitJson = await submitRes.json();
    const createdId = submitJson.data?.id;
    console.log('Task submitted, status:', submitRes.status(), 'ID:', createdId);

    results.tests.push({
      name: 'ui-special-passenger-task-submission',
      httpStatus: submitRes.status(),
      createdTaskId: createdId,
      result: submitRes.status() === 200 && !!createdId ? 'P' : 'F'
    });

    // 4. Clarification modal
    console.log('Waiting for clarification modal...');
    await page.waitForSelector('.ant-modal:has-text("补充信息")', { timeout: 6000 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F025-V1.186-ui-clarify-dialog.png') });

    const clarifyModal = page.locator('.ant-modal:has-text("补充信息")');
    const formItems = clarifyModal.locator('.ant-form-item');
    const itemCount = await formItems.count();
    for (let i = 0; i < itemCount; i++) {
      const item = formItems.nth(i);
      const text = await item.innerText();
      const input = item.locator('input');
      if (text.includes('协助类型')) {
        await input.fill('轮椅协助');
      } else if (text.includes('起点')) {
        await input.fill('F2_GATE_A');
      } else if (text.includes('目的地')) {
        await input.fill('F2_SERVICE_POINT');
      } else {
        await input.fill('F2_GATE_A');
      }
    }
    if (itemCount === 0) {
      await clarifyModal.locator('input').first().fill('F2_GATE_A');
    }
    await page.waitForTimeout(300);

    const [clarifyRes] = await Promise.all([
      page.waitForResponse(r => r.url().includes(`/api/v1/tasks/${createdId}/clarify`) && r.request().method() === 'POST'),
      clarifyModal.locator('.ant-modal-footer button.ant-btn-primary').click()
    ]);
    console.log('Clarification submitted, status:', clarifyRes.status());
    await page.waitForTimeout(1000);

    results.tests.push({
      name: 'ui-special-passenger-clarification',
      httpStatus: clarifyRes.status(),
      clarifiedTaskId: createdId,
      result: clarifyRes.status() === 200 ? 'P' : 'F'
    });

    // 5. Navigate to task detail page to inspect special passenger card
    console.log(`Navigating to task detail /tasks/${createdId}...`);
    await page.goto(`http://127.0.0.1:15179/tasks/${createdId}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F025-V1.186-ui-special-passenger-card.png'), fullPage: true });

    const pageText = await page.locator('body').innerText();
    const hasCardTitle = pageText.includes('特殊旅客协助与陪同协同服务') || pageText.includes('特殊旅客服务') || pageText.includes('特殊旅客');
    const hasAssistanceType = pageText.includes('轮椅协助') || pageText.includes('协助类型');
    const hasOrigin = pageText.includes('F2_GATE_A') || pageText.includes('服务起点');
    const hasStatusAlert = pageText.includes('执行中') || pageText.includes('进行中') || pageText.includes('已完成') || pageText.includes('服务指引') || pageText.includes('协助接续') || pageText.includes('保障指引');

    const cardPassed = hasCardTitle && hasAssistanceType && hasOrigin;
    results.tests.push({
      name: 'ui-special-passenger-card-render',
      taskId: createdId,
      hasCardTitle,
      hasAssistanceType,
      hasOrigin,
      hasStatusAlert,
      result: cardPassed ? 'P' : 'F'
    });
    console.log('Special passenger card UI test result:', cardPassed ? 'P' : 'F');

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
