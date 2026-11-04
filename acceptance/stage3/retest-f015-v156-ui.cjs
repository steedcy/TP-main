// Real Edge headless actions. Credentials are local inputs and are never saved in evidence.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),dir=path.join(__dirname,'evidence');
const {chromium}=require(process.env.PLAYWRIGHT_CORE_PATH||path.join(root,'../tip/.local-test/node_modules/playwright-core'));
const mode=process.argv[2]||'details',base='http://127.0.0.1:15179';
const state=JSON.parse(fs.readFileSync(path.join(root,'.local-test/f015-v156-state.json'),'utf8'));
const suite=JSON.parse(fs.readFileSync(path.join(dir,'SRS_F015-V1.156-full-round-20261104.json'),'utf8'));
const accounts=Object.fromEntries(fs.readFileSync(path.join(root,'../tip/user.md'),'utf8').split(/\r?\n/)
 .filter(x=>/^\|(?:运行操作员|配置管理员)\|/.test(x)).map(x=>{const[,role,username,password]=x.split('|').map(v=>v.trim());return[role,{username,password}]}));
const out=path.join(dir,`SRS_F015-V1.156-ui-${mode}-20261104.json`);
const shot=name=>path.join(dir,`SRS_F015-V1.156-ui-${name}-20261104.png`);
const javascriptErrors=[];
async function login(browser,role){
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('pageerror',error=>javascriptErrors.push({url:page.url(),message:String(error)}));
 await page.goto(base+'/login',{waitUntil:'networkidle'});await page.getByPlaceholder('账号').fill(accounts[role].username);
 await page.getByPlaceholder('密码').fill(accounts[role].password);await page.locator('button[type=submit]').click();await page.waitForURL('**/overview');return page;
}
async function closeDialog(page){const dialog=page.getByRole('dialog');await dialog.getByRole('button',{name:/关\s*闭/}).click();await dialog.waitFor({state:'hidden'});}
async function dialogData(page){
 const d=page.getByRole('dialog');await d.getByText('参数映射：',{exact:true}).first().waitFor();
 const label=d.locator('.ant-descriptions-item-label').filter({hasText:/^模板版本$/});
 return{text:await d.innerText(),version:await label.locator('xpath=following-sibling::td[1]').innerText(),
  editableInputs:await d.locator('input:not([disabled]):not([readonly]),textarea:not([readonly]),select').count(),
  writeButtons:await d.getByRole('button').filter({hasText:/保存|确[认定]|编\s*辑|删\s*除|添\s*加|试运行/}).count()};
}
async function findRow(page,name){
 await page.locator('.ant-pagination-item').first().waitFor();
 const pages=await page.locator('.ant-pagination-item').allTextContents();
 for(const n of pages){await page.locator(`.ant-pagination-item[title="${n.trim()}"]`).click();const row=page.getByRole('row').filter({hasText:name});if(await row.count())return row;}
 throw new Error('Template row absent: '+name);
}
async function main(){
 if(fs.existsSync(out))throw new Error('Do not overwrite UI evidence');
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const e={tag:'V1.156',productSha:'5effea7e267f5ef724a00a58716c67a59b284272',executionBaseline:'V2.4',mode,
  startedAt:new Date().toISOString(),timezone:'Asia/Shanghai',browser:browser.version(),checks:{},cases:[],javascriptErrors};
 const save=()=>fs.writeFileSync(out,JSON.stringify(e,null,2)+'\n');
 try{
  const page=await login(browser,'运行操作员');
  if(mode==='manual'){
   const tid=Number(process.argv[3]);e.taskId=tid;await page.goto(base+'/tasks/'+tid,{waitUntil:'networkidle'});
   e.before=await page.locator('body').innerText();await page.getByRole('button',{name:'转基线执行',exact:true}).click();
   await page.waitForTimeout(600);e.after=await page.locator('body').innerText();e.checks.clickedRealManualAction=true;
   await page.screenshot({path:shot('manual-switch'),fullPage:true});save();return;
  }
  if(mode==='frozen'){
   const recovery=JSON.parse(fs.readFileSync(path.join(dir,'SRS_F015-V1.156-full-round-20261104.json'),'utf8'));
   const frozen=recovery.cases.find(x=>x.name==='frozen-live-edit');e.taskId=frozen.taskId;
   await page.goto(base+'/tasks/'+frozen.taskId,{waitUntil:'networkidle'});
   const ref=page.locator('[data-testid=baseline-template-ref]');await ref.waitFor();e.reference=await ref.innerText();
   e.checks.frozenAndCurrentVersionDistinguished=e.reference.includes('V1.0')&&e.reference.includes('V1.1');
   await ref.getByRole('button',{name:'查看详情',exact:true}).first().click();e.currentTemplateDialog=await dialogData(page);
   e.checks.readonlyCurrentDetails=e.currentTemplateDialog.editableInputs===0&&e.currentTemplateDialog.writeButtons===0;
   e.expectedCurrentVersion=frozen.templateAfterEdit.templateVersion;e.checks.currentVersionExact=e.currentTemplateDialog.version===e.expectedCurrentVersion;
   e.note='Execution immutability is proved by current task262 API/SQL before/after. UI explicitly distinguishes frozen V1.0 from current V1.1; the modal reads current template configuration.';
   await page.screenshot({path:shot('frozen-version-reference'),fullPage:true});e.result=Object.values(e.checks).every(Boolean)?'P':'F';save();return;
  }
  const high=suite.cases.find(x=>x.name==='high-valid'),tid=high.taskId;
  const templateId=state.uiTemplateId,templateName=high.observed.plans.at(-1).baselineTemplateId===templateId
   ?suite.trials.find(x=>x.templateId===templateId).templateAfterTrial.templateName:null;
  e.taskId=tid;e.templateId=templateId;e.templateName=templateName;
  await page.goto(base+'/tasks/'+tid,{waitUntil:'networkidle'});
  const ref=page.locator('[data-testid=baseline-template-ref]');await ref.waitFor();
  e.taskDetail={body:await page.locator('body').innerText(),reference:await ref.innerText(),links:await ref.locator('a').evaluateAll(xs=>xs.map(a=>({text:a.textContent,href:a.getAttribute('href')})))};
  e.checks.fixedSource=e.taskDetail.body.includes('固定来源基线模板');
  e.checks.matchBasis=['任务族 / 模板意图','所需能力','步骤数上限'].every(x=>e.taskDetail.body.includes(x));
  await page.locator('[data-testid=prior-plan-link]').click();e.priorTab=await page.getByRole('tab',{selected:true}).innerText();e.checks.priorPlanLink=e.priorTab.includes('版本1');
  await page.getByRole('tab',{name:'版本2（基线模板）'}).click();
  await ref.getByRole('button',{name:'查看详情',exact:true}).first().click();e.taskDirectDialog=await dialogData(page);
  e.checks.taskDirectReadOnly=e.taskDirectDialog.editableInputs===0&&e.taskDirectDialog.writeButtons===0&&e.taskDirectDialog.text.includes('参数映射');
  e.checks.taskModalVersionExact=e.taskDirectDialog.version==='V1.0';
  await page.screenshot({path:shot('task-readonly-detail'),fullPage:true});await closeDialog(page);
  await ref.locator('a[href="/baseline-templates"]').first().click();await page.waitForURL('**/baseline-templates');
  let row=await findRow(page,templateName);e.operatorRow={text:await row.innerText(),links:await row.locator('a').count(),buttons:await row.getByRole('button').count()};
  await row.locator('[data-testid=template-name-link]').click();e.listNameDialog=await dialogData(page);
  e.checks.nameLinkOpensReadonly=e.operatorRow.links>=1&&e.listNameDialog.editableInputs===0&&e.listNameDialog.text.includes('参数映射');
  e.checks.listModalVersionExact=e.listNameDialog.version==='V1.0';
  await page.screenshot({path:shot('operator-list-readonly'),fullPage:true});await closeDialog(page);
  await row.locator('[data-testid=view-template-btn]').click();e.viewButtonDialog=await dialogData(page);
  e.checks.viewButtonOpensReadonly=e.operatorRow.buttons>=1&&e.viewButtonDialog.writeButtons===0;await closeDialog(page);
  await page.goto(base+'/tasks/'+tid,{waitUntil:'networkidle'});await page.locator('[data-testid=baseline-template-ref]').waitFor();
  await page.locator('[data-testid=baseline-template-ref] a[href="/baseline-templates"]').last().click();await page.waitForURL('**/baseline-templates');
  row=await findRow(page,templateName);await row.locator('[data-testid=view-template-btn]').click();e.versionLinkDialog=await dialogData(page);e.checks.frozenVersionEntryCanView=e.versionLinkDialog.text.includes('参数映射');await closeDialog(page);
  await page.goto(base+'/baseline-templates?templateId='+templateId,{waitUntil:'networkidle'});e.queryDirectDialog=await dialogData(page);e.checks.queryDirect=e.queryDirectDialog.text.includes(templateName);await closeDialog(page);
  // Preserve the original 234/39 counterexample as a direct UI regression too.
  await page.goto(base+'/baseline-templates?templateId=39',{waitUntil:'networkidle'});e.original39=await dialogData(page);e.checks.original39Readonly=e.original39.text.includes('G154 F015 newer-trial-B')&&e.original39.editableInputs===0;await closeDialog(page);
  const cfg=await login(browser,'配置管理员');await cfg.goto(base+'/baseline-templates?templateId='+templateId,{waitUntil:'networkidle'});e.configReadonly=await dialogData(cfg);e.checks.configReadonly=e.configReadonly.editableInputs===0;await closeDialog(cfg);
  const cr=await findRow(cfg,templateName);await cr.getByRole('button',{name:/编\s*辑/}).click();await cfg.getByRole('dialog').waitFor();
  e.configEditControl={text:await cfg.getByRole('dialog').innerText(),enabledInputs:await cfg.getByRole('dialog').locator('input:not([disabled])').count()};e.checks.configCanEdit=e.configEditControl.enabledInputs>0;
  await cfg.screenshot({path:shot('config-admin-control'),fullPage:true});
  const frozen=suite.cases.find(x=>x.name==='frozen-live-edit'&&x.observed);
  if(frozen){await page.goto(base+'/tasks/'+frozen.taskId,{waitUntil:'networkidle'});await page.locator('[data-testid=baseline-template-ref]').waitFor();e.frozenTaskReference=await page.locator('[data-testid=baseline-template-ref]').innerText();e.checks.frozenVersionDistinguished=e.frozenTaskReference.includes('V1.0')&&e.frozenTaskReference.includes('V1.1');await page.screenshot({path:shot('frozen-current-version-distinction'),fullPage:true});}
  e.result=Object.values(e.checks).every(Boolean)?'P':'F';save();
 }catch(err){e.probeError=String(err);save();throw err;}
 finally{e.finishedAt=new Date().toISOString();save();await browser.close();}
 process.stdout.write(JSON.stringify({mode,result:e.result,checks:e.checks})+'\n');
}
main().catch(err=>{process.stderr.write(String(err)+'\n');process.exitCode=1});
