// Real Edge controls and HTTP responses. No response interception or credentials in evidence.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),dir=path.join(__dirname,'evidence');
const {chromium}=require(path.join(root,'../tip/.local-test/node_modules/playwright-core'));
const accounts=Object.fromEntries(fs.readFileSync(path.join(root,'../tip/user.md'),'utf8').split(/\r?\n/).filter(x=>/^\|运行操作员\|/.test(x)).map(x=>{const[,role,username,password]=x.split('|').map(v=>v.trim());return[role,{username,password}]}));
async function main(){
 const mode=process.argv[2]||'details';const out=path.join(dir,mode==='trace'?'SRS_F016-V1.158-ui-trace-20261105.json':mode==='views'?'SRS_F016-V1.158-ui-views-20261105.json':'SRS_F016-V1.158-ui-20261105.json');if(fs.existsSync(out))throw Error('Do not overwrite evidence');
 const suite=JSON.parse(fs.readFileSync(path.join(dir,'SRS_F016-V1.158-http-20261105.json'),'utf8')); const extra=JSON.parse(fs.readFileSync(path.join(dir,'SRS_F016-V1.158-baseline-controls-20261105.json'),'utf8')); suite.cases.push(...extra.cases);
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1800,height:1100}}),page=await context.newPage();page.setDefaultTimeout(20000);
 const ev={tag:'V1.158',productSha:'4f0b4d8e0ab2a2f0e4027d3ee21b20fe487dcadc',baseline:'V2.4/BL006',at:new Date().toISOString(),timezone:'Asia/Shanghai',browser:browser.version(),javascriptErrors:[],pages:[]};
 const save=()=>fs.writeFileSync(out,JSON.stringify(ev,null,2)+'\n');page.on('pageerror',e=>ev.javascriptErrors.push(String(e)));
 try{
  await page.goto('http://127.0.0.1:15179/login',{waitUntil:'networkidle'});await page.getByPlaceholder('账号').fill(accounts['运行操作员'].username);await page.getByPlaceholder('密码').fill(accounts['运行操作员'].password);await page.locator('button[type=submit]').click();await page.waitForURL('**/overview');
  for(const name of (mode!=='details'?[]:['rank-match','reject-next','baseline-all-reject'])){
   const row=suite.cases.find(r=>r.name===name),id=row.taskId;
   const rp=page.waitForResponse(r=>r.url().includes(`/tasks/${id}/step-assignments`)&&r.status()===200);
   await page.goto('http://127.0.0.1:15179/tasks/'+id,{waitUntil:'networkidle'});const api=(await (await rp).json()).data;
   await page.locator('#step-assignments').waitFor();const text=await page.locator('body').innerText(),assignmentText=await page.locator('#step-assignments').innerText();
   await page.locator('#step-assignments').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(dir,`SRS_F016-V1.158-ui-${name}-20261105.png`),fullPage:true});
   ev.pages.push({name,taskId:id,text,assignmentText,api,checks:{responseColumnVisible:assignmentText.includes('承接响应时间'),numericDurationVisible:/\d+ms/.test(assignmentText),durationMatchesApi:api.length>0&&api.every(a=>a.acceptanceDurationMs!=null&&assignmentText.includes(a.acceptanceDurationMs+'ms')),timestampsMatchDuration:api.every(a=>Math.abs((Date.parse(a.acceptedAt)-Date.parse(a.acceptanceRequestedAt))-a.acceptanceDurationMs)<=1),rejectionVisible:name==='rank-match'||text.includes('SYNTHETIC_CAPACITY_REJECTED')}});save();
  }
  const failed=suite.cases.find(r=>r.name==='baseline-all-reject'),taskCode=failed.after.task.taskCode;
  if(mode!=='trace'){await page.goto('http://127.0.0.1:15179/task-exceptions',{waitUntil:'networkidle'});await page.locator('.ant-select').first().click();await page.locator('.ant-select-dropdown:visible').getByText('分配失败',{exact:true}).click();await page.locator('[data-testid=exception-scope]').getByText(/^全部/).click();await page.waitForTimeout(500);
  const text=await page.locator('body').innerText();ev.exceptionFilter={taskCode,text,checks:{typeMapped:text.includes('分配失败'),taskListed:text.includes('任务#'+failed.taskId)}};await page.screenshot({path:path.join(dir,'SRS_F016-V1.158-ui-exception-filter-20261105.png'),fullPage:true});save();}
  await page.goto('http://127.0.0.1:15179/task-trace',{waitUntil:'networkidle'});await page.getByPlaceholder('任务编号（精确）').fill(taskCode);await page.getByRole('button',{name:/查\s*询/}).click();const item=page.locator('.ant-list-item').filter({hasText:taskCode});await item.waitFor();await item.click();await page.getByText('STEP_ASSIGNMENT_FAILED',{exact:true}).first().waitFor();
  const trace=await page.locator('body').innerText();ev.trace={taskCode,text:trace,checks:{assignmentFailureReasonVisible:trace.includes('ASSIGNMENT_FAILED'),failureEventVisible:trace.includes('STEP_ASSIGNMENT_FAILED')}};await page.screenshot({path:path.join(dir,'SRS_F016-V1.158-ui-trace-20261105.png'),fullPage:true});save();
 }catch(e){ev.diagnostic={message:e.message};save();throw e;}finally{save();await browser.close();}
 console.log(JSON.stringify({pages:ev.pages.map(p=>({name:p.name,checks:p.checks})),exceptionFilter:ev.exceptionFilter?.checks,trace:ev.trace?.checks}));
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
