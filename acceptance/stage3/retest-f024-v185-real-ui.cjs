const fs = require('fs');
const path = require('path');
const { chromium } = require('C:/Users/savy/Desktop/TIP-main/tip/.local-test/node_modules/playwright-core');

const root = path.resolve(__dirname, '../..');
const evidenceDir = path.join(__dirname, 'evidence');
const outFile = path.join(evidenceDir, 'SRS_F024-V1.185-real-ui-results.json');

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
    // 1. Login as CONFIG_ADMIN (set / 12345678)
    console.log('Logging in as set (CONFIG_ADMIN)...');
    await page.goto('http://127.0.0.1:15179/login', { waitUntil: 'networkidle' });
    await page.getByPlaceholder('账号').fill('set');
    await page.getByPlaceholder('密码').fill('12345678');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL('**/overview');

    // 2. Navigate to /simulators
    console.log('Navigating to /simulators as CONFIG_ADMIN...');
    await page.goto('http://127.0.0.1:15179/simulators', { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F024-V1.185-ui-simulators-console.png'), fullPage: true });

    // 3. Normal measurement test on UI
    console.log('Testing normal measurement in UI...');
    await page.locator('input[placeholder="如 T2值机岛A03"]').fill('F2_TEST_SERVICE');
    const inputs = await page.locator('.ant-input-number-input').all();
    if (inputs.length >= 4) {
      await inputs[0].fill('55');
      await inputs[1].fill('40');
      await inputs[2].fill('20');
      await inputs[3].fill('10');
    }
    await page.locator('input[placeholder="选填，默认专柜"]').fill('F2_TEST_GATE');
    await page.waitForTimeout(200);

    const [normalRes] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/v1/tasks/measurement-event') && r.request().method() === 'POST'),
      page.locator('button[data-testid="btn-submit-measurement"]').click()
    ]);
    const normalJson = await normalRes.json();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F024-V1.185-ui-normal-measurement-result.png'), fullPage: true });

    const normalText = await page.locator('body').innerText();
    const normalPassed = normalRes.status() === 200 && normalText.includes('正常行李') && normalText.includes('COMPLETED');
    results.tests.push({
      name: 'ui-simulators-normal-measurement',
      httpStatus: normalRes.status(),
      responseData: normalJson,
      tagDetected: normalText.includes('正常行李'),
      statusCompleted: normalText.includes('COMPLETED'),
      result: normalPassed ? 'P' : 'F'
    });
    console.log('Normal measurement UI test result:', normalPassed ? 'P' : 'F');

    // 4. Oversize measurement test on UI
    console.log('Testing oversize measurement in UI...');
    await page.getByText('填入超规示例').click();
    await page.waitForTimeout(200);

    const [oversizeRes] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/v1/tasks/measurement-event') && r.request().method() === 'POST'),
      page.locator('button[data-testid="btn-submit-measurement"]').click()
    ]);
    const oversizeJson = await oversizeRes.json();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F024-V1.185-ui-oversize-measurement-result.png'), fullPage: true });

    const oversizeText = await page.locator('body').innerText();
    const oversizePassed = oversizeRes.status() === 200 && oversizeText.includes('超规行李');
    results.tests.push({
      name: 'ui-simulators-oversize-measurement',
      httpStatus: oversizeRes.status(),
      responseData: oversizeJson,
      tagDetected: oversizeText.includes('超规行李'),
      result: oversizePassed ? 'P' : 'F'
    });
    console.log('Oversize measurement UI test result:', oversizePassed ? 'P' : 'F');

    // 5. Login as OPERATOR (oprator / 12345678)
    console.log('Logging in as oprator (OPERATOR)...');
    await page.goto('http://127.0.0.1:15179/login', { waitUntil: 'networkidle' });
    await page.getByPlaceholder('账号').fill('oprator');
    await page.getByPlaceholder('密码').fill('12345678');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL('**/overview');

    // 6. Access /simulators as OPERATOR
    console.log('Verifying /simulators access as OPERATOR...');
    await page.goto('http://127.0.0.1:15179/simulators', { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F024-V1.185-ui-operator-simulators.png'), fullPage: true });
    const opSimText = await page.locator('body').innerText();
    const opSimAccessible = opSimText.includes('模拟行李测量事件触发') || opSimText.includes('仿真场景控制');
    results.tests.push({
      name: 'ui-operator-simulators-accessible',
      accessible: opSimAccessible,
      result: opSimAccessible ? 'P' : 'F'
    });
    console.log('Operator simulators UI access result:', opSimAccessible ? 'P' : 'F');

    // 7. Submit F185_UI_GOAL on /tasks
    console.log('Navigating to /tasks as OPERATOR to submit F185_UI_GOAL...');
    await page.goto('http://127.0.0.1:15179/tasks', { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: '提交任务', exact: true }).click();
    await page.waitForTimeout(400);

    await page.locator('textarea').fill('F185_UI_GOAL 协助旅客处理超规行李并引导至超规柜台');
    await page.waitForTimeout(200);
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F024-V1.185-ui-goal-submission.png') });

    const [submitRes] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/v1/tasks') && r.request().method() === 'POST'),
      page.locator('.ant-modal-footer button.ant-btn-primary').click()
    ]);
    const submitJson = await submitRes.json();
    await page.waitForTimeout(800);
    const createdId = submitJson.data?.id;
    console.log('Submitted UI task response:', submitRes.status(), 'Created Task ID:', createdId);
    results.tests.push({
      name: 'ui-task-goal-submission',
      httpStatus: submitRes.status(),
      createdTaskId: createdId,
      result: submitRes.status() === 200 && !!createdId ? 'P' : 'F'
    });

    // 8. Clarification modal opens automatically on /tasks
    console.log('Verifying clarification modal in UI...');
    await page.waitForSelector('.ant-modal:has-text("补充信息")', { timeout: 5000 });
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F024-V1.185-ui-clarify-before.png') });

    const clarifyModal = page.locator('.ant-modal:has-text("补充信息")');
    const modalInput = clarifyModal.locator('input').first();
    await modalInput.fill('F2_TEST_SERVICE');
    await page.waitForTimeout(300);

    const [clarifyRes] = await Promise.all([
      page.waitForResponse(r => r.url().includes(`/api/v1/tasks/${createdId}/clarify`) && r.request().method() === 'POST'),
      clarifyModal.locator('.ant-modal-footer button.ant-btn-primary').click()
    ]);
    const clarifyJson = await clarifyRes.json();
    console.log('Clarification UI response:', clarifyRes.status(), clarifyJson);
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(evidenceDir, 'SRS_F024-V1.185-ui-clarify-after.png') });

    results.tests.push({
      name: 'ui-task-clarification-submission',
      httpStatus: clarifyRes.status(),
      clarifiedTaskId: createdId,
      result: clarifyRes.status() === 200 ? 'P' : 'F'
    });

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
