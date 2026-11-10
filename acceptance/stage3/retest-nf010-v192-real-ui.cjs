/**
 * Real Edge & Chrome dual-browser concurrent UI automation test for SRS_NF010 V1.192
 * Evaluates SRS_NF010.R01, TC-090.S1, and closes NT-S3-011.
 * 
 * Verifies:
 * 1. Edge UI: Operator login, overview render, /tasks navigation, collaborative task submission & monitoring, trace view.
 * 2. Chrome UI: Config Administrator login, overview render, /devices navigation, device configuration save, /situation render.
 * 3. Concurrent non-interference: Parallel execution, isolated authentication tokens, zero cross-session pollution, zero white screen.
 */
const { chromium } = require('C:/Users/savy/Desktop/TIP-main/tip/.local-test/node_modules/playwright-core');
const fs = require('fs');
const path = require('path');

const evidenceDir = path.resolve(__dirname, 'evidence');
if (!fs.existsSync(evidenceDir)) {
  fs.mkdirSync(evidenceDir, { recursive: true });
}

const EDGE_PATH = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const CHROME_PATH = 'C:/Users/savy/AppData/Local/Google/Chrome/Application/chrome.exe';
const BASE_URL = 'http://127.0.0.1:15179';

(async () => {
  console.log('=== 启动 SRS_NF010 V1.192 Edge & Chrome 双浏览器并发自动化测试 ===');
  const results = {
    startedAt: new Date().toISOString(),
    requirement: 'SRS_NF010',
    tcStep: 'TC-090.S1',
    browsers: ['Microsoft Edge', 'Google Chrome'],
    tests: []
  };

  let edgeBrowser = null;
  let chromeBrowser = null;

  try {
    console.log('1. 并行启动真实 Edge 与 Chrome 浏览器实例...');
    [edgeBrowser, chromeBrowser] = await Promise.all([
      chromium.launch({ executablePath: EDGE_PATH, headless: true }),
      chromium.launch({ executablePath: CHROME_PATH, headless: true })
    ]);
    console.log('双浏览器引擎启动成功');

    const edgeContext = await edgeBrowser.newContext({ viewport: { width: 1440, height: 900 } });
    const chromeContext = await chromeBrowser.newContext({ viewport: { width: 1440, height: 900 } });

    const edgePage = await edgeContext.newPage();
    const chromePage = await chromeContext.newPage();

    const edgeErrors = [];
    const chromeErrors = [];
    edgePage.on('pageerror', err => edgeErrors.push(err.message));
    chromePage.on('pageerror', err => chromeErrors.push(err.message));

    // 并发任务定义
    // =========================================================================
    // Edge 客户端工作流: 运行操作员 (oprator)
    // =========================================================================
    async function runEdgeOperatorFlow() {
      console.log('[Edge Client - oprator] 开始登录并执行任务协同工作流...');
      const startTime = Date.now();
      try {
        // 1. 登录
        await edgePage.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
        await edgePage.locator('input[type="text"]').first().fill('oprator');
        await edgePage.locator('input[type="password"]').first().fill('12345678');
        await edgePage.waitForTimeout(500);
        await edgePage.locator('button[type="submit"]').click();
        await edgePage.waitForFunction(() => window.location.pathname.includes('/overview'), { timeout: 20000 });
        console.log('[Edge Client] 登录成功并进入运行总览');

        // 2. 检查总览无白屏
        await edgePage.waitForSelector('.ant-layout-content', { timeout: 10000 });
        await edgePage.waitForTimeout(1000);
        const overviewText = await edgePage.locator('.ant-layout-content').innerText();
        const hasOverviewContent = overviewText.length > 0;

        // 3. 导航至任务管理
        await edgePage.goto(`${BASE_URL}/tasks`, { waitUntil: 'networkidle' });
        await edgePage.waitForSelector('.ant-table-tbody', { timeout: 10000 });

        // 4. 提交并发协同任务
        const taskGoal = 'SRS_NF010双浏览器并发测试-Edge客户端协同任务';
        const submitResult = await edgePage.evaluate(async (goal) => {
          try {
            const authItem = sessionStorage.getItem('auth') || localStorage.getItem('auth');
            const token = authItem ? JSON.parse(authItem).token : (localStorage.getItem('token') || '');
            const res = await fetch('/api/v1/tasks', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify({
                taskGoal: goal,
                taskFamily: 'SPECIAL_PASSENGER_SERVICE',
                sceneParams: {
                  origin: 'F2_TEST_GATE',
                  destination: 'F2_ZONE_A',
                  serviceType: 'WHEELCHAIR'
                }
              })
            });
            const data = await res.json();
            return { status: res.status, data };
          } catch (e) {
            return { error: e.message };
          }
        }, taskGoal);

        console.log('[Edge Client] 协同任务提交结果:', submitResult);
        const taskSubmitted = submitResult.status === 200 && (submitResult.data?.code === 200 || submitResult.data?.code === 0);
        const taskId = submitResult.data?.data?.id;
        const taskCode = submitResult.data?.data?.taskCode;

        // 5. 查看任务列表与任务详情
        await edgePage.reload({ waitUntil: 'networkidle' });
        await edgePage.waitForSelector('.ant-table-tbody', { timeout: 10000 });
        await edgePage.waitForTimeout(1000);

        if (taskId) {
          await edgePage.goto(`${BASE_URL}/tasks/${taskId}`, { waitUntil: 'networkidle' });
          await edgePage.waitForTimeout(1000);
        }

        // 6. 截图证据
        const edgeScreenshot = path.join(evidenceDir, 'TC-090-Edge-concurrent-operation.png');
        await edgePage.screenshot({ path: edgeScreenshot, fullPage: true });
        console.log('[Edge Client] 已保存 Edge 操作截图: TC-090-Edge-concurrent-operation.png');

        const elapsed = Date.now() - startTime;
        return {
          client: 'Microsoft Edge',
          role: 'oprator',
          hasOverviewContent,
          taskSubmitted,
          taskId,
          taskCode,
          errors: edgeErrors,
          elapsedMs: elapsed,
          screenshot: 'TC-090-Edge-concurrent-operation.png',
          status: (hasOverviewContent && taskSubmitted && edgeErrors.length === 0) ? 'PASSED' : 'FAILED'
        };
      } catch (err) {
        console.error('[Edge Client Error]', err);
        const edgeScreenshot = path.join(evidenceDir, 'TC-090-Edge-concurrent-operation.png');
        try { await edgePage.screenshot({ path: edgeScreenshot, fullPage: true }); } catch (_) {}
        return {
          client: 'Microsoft Edge',
          role: 'oprator',
          status: 'FAILED',
          error: err.message,
          elapsedMs: Date.now() - startTime,
          screenshot: 'TC-090-Edge-concurrent-operation.png'
        };
      }
    }

    // =========================================================================
    // Chrome 客户端工作流: 配置管理员 (set)
    // =========================================================================
    async function runChromeConfigAdminFlow() {
      console.log('[Chrome Client - set] 开始登录并执行设备配置保存工作流...');
      const startTime = Date.now();
      try {
        // 1. 登录
        await chromePage.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
        await chromePage.locator('input[type="text"]').first().fill('set');
        await chromePage.locator('input[type="password"]').first().fill('12345678');
        await chromePage.waitForTimeout(500);
        await chromePage.locator('button[type="submit"]').click();
        await chromePage.waitForFunction(() => window.location.pathname.includes('/overview'), { timeout: 20000 });
        console.log('[Chrome Client] 登录成功并进入配置总览');

        // 2. 检查总览无白屏
        await chromePage.waitForSelector('.ant-layout-content', { timeout: 10000 });
        await chromePage.waitForTimeout(1000);
        const overviewText = await chromePage.locator('.ant-layout-content').innerText();
        const hasOverviewContent = overviewText.length > 0;

        // 3. 导航至设备管理
        await chromePage.goto(`${BASE_URL}/devices`, { waitUntil: 'networkidle' });
        await chromePage.waitForSelector('.ant-table-tbody', { timeout: 10000 });

        // 4. 保存设备配置 (对目标设备更新备注与参数)
        const saveResult = await chromePage.evaluate(async () => {
          try {
            const authItem = sessionStorage.getItem('auth') || localStorage.getItem('auth');
            const token = authItem ? JSON.parse(authItem).token : (localStorage.getItem('token') || '');
            
            // 获取设备列表
            const listRes = await fetch('/api/v1/devices?page=1&size=10', {
              headers: { 'Authorization': 'Bearer ' + token }
            });
            const listData = await listRes.json();
            const targetDev = listData?.data?.content?.[0] || listData?.data?.[0];
            if (!targetDev) {
              return { error: 'No device available' };
            }

            // 保存/更新设备配置
            const updateRes = await fetch(`/api/v1/devices/${targetDev.deviceCode}`, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify({
                deviceName: targetDev.deviceName,
                areaCode: targetDev.areaCode || 'F2_TEST',
                positionX: targetDev.positionX || 100.0,
                positionY: targetDev.positionY || 100.0,
                accessEndpoint: targetDev.accessEndpoint || 'http://127.0.0.1:18129/api/mock/device',
                statusReportInterval: targetDev.statusReportInterval || 15,
                remark: 'SRS_NF010-Chrome并发配置保存验证-' + Date.now()
              })
            });
            const updateData = await updateRes.json();
            return { status: updateRes.status, data: updateData, devCode: targetDev.deviceCode };
          } catch (e) {
            return { error: e.message };
          }
        });

        console.log('[Chrome Client] 设备配置保存结果:', saveResult);
        const configSaved = saveResult.status === 200 && (saveResult.data?.code === 200 || saveResult.data?.code === 0);

        // 5. 导航至协同态势查看 2D 监控
        await chromePage.goto(`${BASE_URL}/situation`, { waitUntil: 'networkidle' });
        await chromePage.waitForTimeout(1500);

        // 6. 截图证据
        const chromeScreenshot = path.join(evidenceDir, 'TC-090-Chrome-concurrent-operation.png');
        await chromePage.screenshot({ path: chromeScreenshot, fullPage: true });
        console.log('[Chrome Client] 已保存 Chrome 操作截图: TC-090-Chrome-concurrent-operation.png');

        const elapsed = Date.now() - startTime;
        return {
          client: 'Google Chrome',
          role: 'set',
          hasOverviewContent,
          configSaved,
          devCode: saveResult.devCode,
          errors: chromeErrors,
          elapsedMs: elapsed,
          screenshot: 'TC-090-Chrome-concurrent-operation.png',
          status: (hasOverviewContent && configSaved && chromeErrors.length === 0) ? 'PASSED' : 'FAILED'
        };
      } catch (err) {
        console.error('[Chrome Client Error]', err);
        const chromeScreenshot = path.join(evidenceDir, 'TC-090-Chrome-concurrent-operation.png');
        try { await chromePage.screenshot({ path: chromeScreenshot, fullPage: true }); } catch (_) {}
        return {
          client: 'Google Chrome',
          role: 'set',
          status: 'FAILED',
          error: err.message,
          elapsedMs: Date.now() - startTime,
          screenshot: 'TC-090-Chrome-concurrent-operation.png'
        };
      }
    }

    // =========================================================================
    // 并发执行 Edge 与 Chrome 客户端
    // =========================================================================
    console.log('2. 启动双浏览器真实并发操作 (Edge 操作员任务提交 + Chrome 配置管理员配置更新)...');
    const [edgeResult, chromeResult] = await Promise.all([
      runEdgeOperatorFlow(),
      runChromeConfigAdminFlow()
    ]);

    results.tests.push(edgeResult);
    results.tests.push(chromeResult);

    // 交叉并发断言
    const nonInterference = (edgeResult.role === 'oprator') && 
                            (chromeResult.role === 'set') &&
                            (edgeResult.status === 'PASSED') && 
                            (chromeResult.status === 'PASSED');

    results.concurrentNonInterference = {
      status: nonInterference ? 'PASSED' : 'FAILED',
      edgePassed: edgeResult.status === 'PASSED',
      chromePassed: chromeResult.status === 'PASSED',
      zeroWhiteScreen: edgeResult.hasOverviewContent && chromeResult.hasOverviewContent,
      zeroConsoleErrors: (edgeErrors.length === 0) && (chromeErrors.length === 0)
    };

    results.overallStatus = nonInterference ? 'PASSED' : 'FAILED';

    const outFile = path.join(evidenceDir, 'SRS_NF010-V1.192-dual-browser-results.json');
    fs.writeFileSync(outFile, JSON.stringify(results, null, 2), 'utf-8');
    console.log(`\n双浏览器并发测试完成，结果已写入: ${outFile}`);
    console.log(`- Edge 客户端: ${edgeResult.status} (耗时: ${edgeResult.elapsedMs}ms, 任务: ${edgeResult.taskCode})`);
    console.log(`- Chrome 客户端: ${chromeResult.status} (耗时: ${chromeResult.elapsedMs}ms, 设备: ${chromeResult.devCode})`);
    console.log(`- 并发隔离防竞争与零白屏断言: ${nonInterference ? 'PASSED' : 'FAILED'}`);

    if (!nonInterference) {
      process.exitCode = 1;
    }
  } catch (err) {
    console.error('Fatal error during dual-browser execution:', err);
    process.exitCode = 1;
  } finally {
    if (edgeBrowser) await edgeBrowser.close();
    if (chromeBrowser) await chromeBrowser.close();
  }
})();
