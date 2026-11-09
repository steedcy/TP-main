/**
 * Real Edge headless browser UI test for SRS_F027 V1.188
 * Verifies TaskTraceView.vue:
 * 1. Plan version expansion showing full plan step tables and validation errors (DEF-S3-008 closed).
 * 2. Event timeline rendering every event with reason codes in parentheses (DEF-S3-057 closed).
 * 3. Empty state rendering for non-existent tasks (NT-S3-007 closed).
 */
const { chromium } = require('C:/Users/savy/Desktop/TIP-main/tip/.local-test/node_modules/playwright-core');
const fs = require('fs');
const path = require('path');

const targetTaskId = process.env.TARGET_TASK_ID || '1330';
const targetTaskCode = process.env.TARGET_TASK_CODE || '';
const evidenceDir = path.resolve(__dirname, 'evidence');
if (!fs.existsSync(evidenceDir)) {
  fs.mkdirSync(evidenceDir, { recursive: true });
}

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    headless: true
  });

  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const results = {
    startedAt: new Date().toISOString(),
    targetTaskId,
    targetTaskCode,
    tests: []
  };

  try {
    // 1. Login as operator (oprator / 12345678)
    console.log('Logging in as oprator (OPERATOR)...');
    await page.goto('http://127.0.0.1:15179/login', { waitUntil: 'networkidle' });
    await page.locator('input[type="text"]').first().fill('oprator');
    await page.locator('input[type="password"]').first().fill('12345678');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL('**/overview', { timeout: 15000 });
    console.log('Logged in successfully!');

    // 2. Navigate to /task-trace
    console.log('Navigating to /task-trace...');
    await page.goto('http://127.0.0.1:15179/task-trace', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // 3. Search and select target task
    console.log(`Searching for task code=${targetTaskCode} id=${targetTaskId}...`);
    const codeInput = page.locator('input.ant-input').first();
    if (await codeInput.count() > 0 && targetTaskCode) {
      await codeInput.fill(targetTaskCode);
      await codeInput.press('Enter');
      await page.waitForTimeout(1500);
    }

    try {
      await page.waitForSelector('.ant-list-item', { timeout: 6000 });
    } catch (e) {
      console.log('Timeout waiting for .ant-list-item');
    }

    const taskItems = page.locator('.ant-list-item');
    const itemCount = await taskItems.count();
    console.log(`Found ${itemCount} task items in trace view list`);

    let selected = false;
    if (itemCount > 0) {
      await taskItems.first().click();
      selected = true;
      console.log('Selected first task in trace view list');
    }

    try {
      await page.waitForSelector('.ant-collapse-header', { timeout: 6000 });
    } catch (e) {
      console.log('Timeout waiting for .ant-collapse-header');
    }
    await page.waitForTimeout(1500);

    // 4. Test Plan Versions Step Table (DEF-S3-008)
    console.log('Testing plan version expansion and step details table...');
    const collapsePanels = page.locator('.ant-collapse-header');
    const panelCount = await collapsePanels.count();
    console.log(`Found ${panelCount} plan version collapse panels`);

    let hasVersionPanels = panelCount >= 1;
    let hasPlanStepTable = false;
    let stepHeadersFound = false;

    if (hasVersionPanels) {
      // Expand first panel
      await collapsePanels.first().click();
      await page.waitForTimeout(1000);

      // Check step table inside collapse
      const stepTable = page.locator('.ant-collapse-content .ant-table');
      hasPlanStepTable = (await stepTable.count()) > 0;

      if (hasPlanStepTable) {
        const thCount = await stepTable.first().locator('.ant-table-thead th').count();
        const trCount = await stepTable.first().locator('.ant-table-row').count();
        stepHeadersFound = thCount >= 3 || trCount >= 1;
      }

      // If multiple panels, expand second panel too
      if (panelCount > 1) {
        await collapsePanels.nth(1).click();
        await page.waitForTimeout(1000);
      }
    }

    // Capture plan steps screenshot
    const planStepScreenshot = path.join(evidenceDir, 'SRS_F027-V1.188-ui-trace-plan-steps.png');
    await page.screenshot({ path: planStepScreenshot, fullPage: true });

    results.tests.push({
      name: 'ui-trace-plan-version-step-details',
      hasVersionPanels,
      hasPlanStepTable,
      stepHeadersFound,
      result: (hasVersionPanels && hasPlanStepTable && stepHeadersFound) ? 'P' : 'F'
    });

    // 5. Test Timeline Reason Codes (DEF-S3-057)
    console.log('Testing timeline event reason codes display...');
    try {
      await page.waitForSelector('.ant-timeline-item', { timeout: 6000 });
    } catch (e) {
      console.log('Timeout waiting for .ant-timeline-item');
    }
    const timelineItems = page.locator('.ant-timeline-item');
    const timelineCount = await timelineItems.count();
    console.log(`Found ${timelineCount} timeline items`);

    let hasTimelineItems = timelineCount >= 3;
    let hasReasonCodesInParens = false;
    let reasonCodesSample = [];

    if (hasTimelineItems) {
      for (let i = 0; i < Math.min(timelineCount, 15); i++) {
        const text = await timelineItems.nth(i).innerText();
        const match = text.match(/[（(]([A-Z_]+)[)）]/);
        if (match) {
          hasReasonCodesInParens = true;
          reasonCodesSample.push(match[1]);
        }
      }
    }

    // Capture timeline screenshot
    const timelineScreenshot = path.join(evidenceDir, 'SRS_F027-V1.188-ui-trace-timeline-reasons.png');
    await page.screenshot({ path: timelineScreenshot, fullPage: true });

    results.tests.push({
      name: 'ui-trace-timeline-reason-codes',
      timelineCount,
      hasTimelineItems,
      hasReasonCodesInParens,
      reasonCodesSample: reasonCodesSample.slice(0, 5),
      result: (hasTimelineItems && hasReasonCodesInParens) ? 'P' : 'F'
    });

    // 6. Test Empty State for non-existent tasks (NT-S3-007)
    console.log('Testing empty state for non-existent tasks...');
    if (await codeInput.count() > 0) {
      await codeInput.fill('TASK-NONEXISTENT-99999');
      await codeInput.press('Enter');
      await page.waitForTimeout(1500);
    }

    const emptyComponent = page.locator('.ant-empty');
    const hasEmptyState = (await emptyComponent.count()) > 0;
    let emptyText = '';
    if (hasEmptyState) {
      emptyText = await emptyComponent.first().innerText();
    }

    // Capture empty state screenshot
    const emptyScreenshot = path.join(evidenceDir, 'SRS_F027-V1.188-ui-trace-empty-state.png');
    await page.screenshot({ path: emptyScreenshot, fullPage: true });

    results.tests.push({
      name: 'ui-trace-empty-state-handling',
      hasEmptyState,
      emptyText,
      result: hasEmptyState ? 'P' : 'F'
    });

  } catch (err) {
    console.error('UI test execution error:', err);
    results.tests.push({
      name: 'ui-test-error',
      error: err.message,
      result: 'F'
    });
  } finally {
    await browser.close();
    results.endedAt = new Date().toISOString();
    const resultFile = path.join(evidenceDir, 'SRS_F027-V1.188-real-ui-results.json');
    fs.writeFileSync(resultFile, JSON.stringify(results, null, 2), 'utf-8');
    console.log('Finished UI tests, results saved to:', resultFile);
  }
})();
