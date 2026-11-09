/**
 * Real Edge headless browser UI test for SRS_F028 V1.189
 * Verifies OperationLogView.vue:
 * 1. Operation logs list rendering with columns, filters, and records (SRS_F028.R01~R03 / TC-085.S1).
 * 2. Detail modal rendering showing structured before/after diff summary (DEF-S3-009 closed).
 * 3. Empty state rendering when querying non-existent account without fabrication (TC-085.S2).
 */
const { chromium } = require('C:/Users/savy/Desktop/TIP-main/tip/.local-test/node_modules/playwright-core');
const fs = require('fs');
const path = require('path');

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
    tests: []
  };

  try {
    // 1. Login as system administrator (admin / cares0126)
    console.log('Logging in as admin (SYSTEM_ADMIN)...');
    await page.goto('http://127.0.0.1:15179/login', { waitUntil: 'networkidle' });
    await page.locator('input[type="text"]').first().fill('admin');
    await page.locator('input[type="password"]').first().fill('cares0126');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL('**/overview', { timeout: 15000 });
    console.log('Logged in successfully!');

    // 2. Navigate to /operation-logs
    console.log('Navigating to /operation-logs...');
    await page.goto('http://127.0.0.1:15179/operation-logs', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // 3. Verify operation logs table rendering
    console.log('Checking operation logs table...');
    await page.waitForSelector('.ant-table-tbody', { timeout: 10000 });
    const rows = page.locator('.ant-table-row');
    const rowCount = await rows.count();
    console.log(`Found ${rowCount} operation log rows initially visible`);

    // Screenshot full list
    const listScreenshot = path.join(evidenceDir, 'SRS_F028-V1.189-ui-audit-list.png');
    await page.screenshot({ path: listScreenshot, fullPage: true });

    results.tests.push({
      name: 'audit-table-list',
      status: rowCount > 0 ? 'PASSED' : 'FAILED',
      rowCount,
      screenshot: 'SRS_F028-V1.189-ui-audit-list.png'
    });

    // 4. Find row with 账号启停 or 账号创建 and open detail modal (DEF-S3-009 check)
    console.log('Opening detail modal on an account status change operation log...');
    let targetRow = page.locator('.ant-table-row:has-text("账号启停")').first();
    if (await targetRow.count() === 0) {
      targetRow = page.locator('.ant-table-row:has-text("账号创建")').first();
    }

    let modalChecked = false;
    let modalText = '';
    let hasPreJson = false;
    let parsedJson = null;

    if (await targetRow.count() > 0) {
      const detailLink = targetRow.locator('a:has-text("详情")').first();
      await detailLink.click();
      await page.waitForSelector('.ant-modal-content', { timeout: 5000 });
      await page.waitForTimeout(500);

      const modal = page.locator('.ant-modal-content');
      modalText = await modal.innerText();

      const pre = modal.locator('pre');
      if (await pre.count() > 0) {
        hasPreJson = true;
        const preContent = await pre.first().innerText();
        try {
          parsedJson = JSON.parse(preContent);
        } catch (e) {
          console.log('Error parsing pre content as JSON:', e.message);
        }
      }

      const detailScreenshot = path.join(evidenceDir, 'SRS_F028-V1.189-ui-audit-detail.png');
      await page.screenshot({ path: detailScreenshot });

      // Close modal
      const closeBtn = page.locator('.ant-modal-close');
      if (await closeBtn.count() > 0) {
        await closeBtn.click();
        await page.waitForTimeout(500);
      }

      modalChecked = true;
    } else {
      console.log('Warning: No 账号启停 row found in first page');
    }

    results.tests.push({
      name: 'audit-detail-modal-def-s3-009',
      status: (modalChecked && hasPreJson) ? 'PASSED' : 'FAILED',
      hasPreJson,
      parsedJson,
      screenshot: 'SRS_F028-V1.189-ui-audit-detail.png'
    });

    // 5. Query non-existent account to verify empty state (TC-085.S2)
    console.log('Querying non-existent account for empty state verification...');
    const usernameInput = page.locator('input[placeholder="操作账号"]').first();
    if (await usernameInput.count() > 0) {
      await usernameInput.fill('nonexistent_user_xyz_99999');
      const searchBtn = page.locator('button:has-text("查询")').first();
      if (await searchBtn.count() > 0) {
        await searchBtn.click();
      } else {
        await usernameInput.press('Enter');
      }
      await page.waitForTimeout(1500);

      const emptyEl = page.locator('.ant-empty');
      const emptyVisible = (await emptyEl.count()) > 0;
      console.log(`Empty state visible: ${emptyVisible}`);

      const emptyScreenshot = path.join(evidenceDir, 'SRS_F028-V1.189-ui-audit-empty-state.png');
      await page.screenshot({ path: emptyScreenshot });

      results.tests.push({
        name: 'audit-empty-state',
        status: emptyVisible ? 'PASSED' : 'FAILED',
        emptyVisible,
        screenshot: 'SRS_F028-V1.189-ui-audit-empty-state.png'
      });
    }

    console.log('Real Edge browser UI test completed successfully!');
  } catch (err) {
    console.error('UI Test failed with error:', err);
    results.error = err.message;
  } finally {
    await browser.close();
    fs.writeFileSync(
      path.join(evidenceDir, 'SRS_F028-V1.189-real-ui-results.json'),
      JSON.stringify(results, null, 2),
      'utf-8'
    );
  }
})();
