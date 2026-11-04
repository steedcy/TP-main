// Real Edge headless UI test; credentials are read locally and never written to evidence.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || path.join(root, '../tip/.local-test/node_modules/playwright-core'));
const evidenceDir = path.join(__dirname, 'evidence');
const label = process.argv[2] ? '-' + process.argv[2] : '';
const artifact = name => path.join(evidenceDir, name.replace('-20261104', '-20261104' + label));
const base = 'http://127.0.0.1:15179';
const caseData = JSON.parse(fs.readFileSync(path.join(evidenceDir, 'SRS_F015-V1.154-live-baseline-20261104.json'), 'utf8'));
const task = caseData.formalCases.at(-1).observed.task;
const used = caseData.templates.at(-1).response;
const accounts = Object.fromEntries(fs.readFileSync(path.join(root, '../tip/user.md'), 'utf8')
  .split(/\r?\n/).filter(line => /^\|(?:运行操作员|配置管理员)\|/.test(line))
  .map(line => { const [, role, username, password] = line.split('|').map(x => x.trim()); return [role, {username, password}]; }));
const out = artifact('SRS_F015-V1.154-operator-template-detail-20261104.json');

async function login(browser, role) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(base + '/login', { waitUntil: 'networkidle' });
  await page.getByPlaceholder('账号').fill(accounts[role].username);
  await page.getByPlaceholder('密码').fill(accounts[role].password);
  await page.locator('button[type=submit]').click();
  await page.waitForURL('**/overview');
  return { context, page };
}

async function findUsedRow(page) {
  await page.locator('.ant-pagination-item').first().waitFor();
  await page.locator('.ant-pagination-item').last().click();
  const row = page.getByRole('row').filter({ hasText: used.templateName });
  await row.waitFor();
  return row;
}

async function main() {
  if (fs.existsSync(out)) throw new Error('Do not overwrite evidence');
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const e = { productSha: '612ff7d39b96e9b947f97f53e6bab6322af87018', tag: 'V1.154',
    startedAt: new Date().toISOString(), timezone: 'Asia/Shanghai', browser: browser.version(),
    layer: 'Real Edge headless DOM/UI clicks/screenshots; no native Windows automation claimed',
    taskId: task.id, templateId: used.id, templateName: used.templateName, checkpoints: [] };
  let page;
  try {
    ({page} = await login(browser, '运行操作员'));
    e.checkpoints.push('operator logged in through real form');
    await page.goto(base + '/tasks/' + task.id, {waitUntil: 'networkidle'});
    const ref = page.locator('[data-testid=baseline-template-ref]');
    await ref.waitFor();
    e.taskDetail = { url: page.url(), body: await page.locator('body').innerText(),
      reference: await ref.innerText(), links: await ref.locator('a').evaluateAll(xs => xs.map(x => ({text:x.textContent,href:x.getAttribute('href')}))) };
    await page.screenshot({path: artifact('SRS_F015-V1.154-ui-task-detail-20261104.png'), fullPage:true});
    await page.locator('[data-testid=prior-plan-link]').click();
    e.priorPlanClick = { selectedTab: await page.getByRole('tab', {selected:true}).innerText() };
    await page.getByRole('tab', {name:'版本2（基线模板）'}).click();
    await ref.locator('a[href="/baseline-templates"]').first().click();
    await page.waitForURL('**/baseline-templates');
    const row = await findUsedRow(page);
    e.operatorRow = { url:page.url(), text:await row.innerText(), linkCount:await row.locator('a').count(), buttonCount:await row.getByRole('button').count() };
    await row.getByText(used.templateName, {exact:true}).click();
    e.afterNameClick = {url:page.url(),dialogCount:await page.getByRole('dialog').count(),body:await page.locator('body').innerText()};
    await page.screenshot({path:artifact('SRS_F015-V1.154-ui-operator-no-detail-20261104.png'),fullPage:true});
    e.checkpoints.push('operator name link navigates to general list; row name clicked without opening detail');
    // The frozen-version link is a separate visible entry; observe its real destination too.
    await page.goto(base + '/tasks/' + task.id, {waitUntil:'networkidle'});
    await page.locator('[data-testid=baseline-template-ref]').waitFor();
    await page.locator('[data-testid=baseline-template-ref] a[href="/baseline-templates"]').last().click();
    await page.waitForURL('**/baseline-templates');
    await findUsedRow(page);
    e.frozenVersionClick = {url:page.url(),dialogCount:await page.getByRole('dialog').count()};
    e.checkpoints.push('operator frozen version link also navigates to same general list');
    const cfg = await login(browser, '配置管理员');
    await cfg.page.goto(base+'/baseline-templates',{waitUntil:'networkidle'});
    const cfgRow=await findUsedRow(cfg.page);
    await cfgRow.getByRole('button',{name:/编\s*辑/}).click();
    const dialog=cfg.page.getByRole('dialog');
    await dialog.waitFor();
    e.configAdminControl={url:cfg.page.url(),dialogText:await dialog.innerText(),
      inputValues:await dialog.locator('input').evaluateAll(xs=>xs.map(x=>({type:x.type,value:x.value,disabled:x.disabled})))};
    await cfg.page.screenshot({path:artifact('SRS_F015-V1.154-ui-config-detail-control-20261104.png'),fullPage:true});
    e.checkpoints.push('config admin can open full detail of same disabled template; no update submitted');
    e.checks={ fixedSourceVisible:e.taskDetail.body.includes('固定来源基线模板'),
      allThreeMatchItemsVisible:['任务族 / 模板意图','所需能力','步骤数上限'].every(x=>e.taskDetail.body.includes(x)),
      priorPlanLinkWorks:e.priorPlanClick.selectedTab.includes('版本1'),
      operatorCannotOpenDetail:e.operatorRow.linkCount===0 && e.operatorRow.buttonCount===0 && e.afterNameClick.dialogCount===0,
      bothLinksLeadOnlyToList:e.afterNameClick.url===base+'/baseline-templates' && e.frozenVersionClick.url===base+'/baseline-templates',
      configAdminCanReadFullDetails:!!e.configAdminControl && e.configAdminControl.dialogText.includes('参数映射') };
    e.result='F';e.issue='DEF-S3-067 (residual, no new defect number)';
  } catch (err) {
    e.probeError=String(err);e.currentUrl=page?.url();
    if(page) e.currentBody=await page.locator('body').innerText().catch(()=>'<unavailable>');
    throw err;
  } finally {
    e.finishedAt=new Date().toISOString();
    fs.writeFileSync(out,JSON.stringify(e,null,2)+'\n');
    await browser.close();
  }
  process.stdout.write(JSON.stringify({result:e.result,checks:e.checks,checkpoints:e.checkpoints})+'\n');
}
main().catch(error=>{process.stderr.write(String(error)+'\n');process.exitCode=1});
