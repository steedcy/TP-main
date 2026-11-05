// Real Edge/SPA operations; task state is supplied by the independent HTTP probe.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const {chromium}=require(path.join(root,'../tip/.local-test/node_modules/playwright-core'));
const [,role,username,password]=fs.readFileSync(path.join(root,'../tip/user.md'),'utf8').split(/\r?\n/).find(x=>/^\|运行操作员\|/.test(x)).split('|').map(x=>x.trim());
(async()=>{
 const [id,phase,completed,total,current]=process.argv.slice(2),dir=path.join(__dirname,'evidence');
 const suffix=process.env.GPT_EVIDENCE_LABEL?'-'+process.env.GPT_EVIDENCE_LABEL:'';const prefix=`SRS_F017-V1.162-ui-${phase}-20261105${suffix}`,out=path.join(dir,prefix+'.json');if(fs.existsSync(out))throw Error('Refusing overwrite');
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1600,height:1050}}),page=await context.newPage(),ev={tag:'V1.162',productSha:'b2623730a0c85622091e6e18bcb1207e23ecdd42',at:new Date().toISOString(),browser:browser.version(),taskId:Number(id),phase,javascriptErrors:[]};
 page.on('pageerror',e=>ev.javascriptErrors.push(String(e)));page.setDefaultTimeout(20000);
 try{
  await page.goto('http://127.0.0.1:15179/login',{waitUntil:'networkidle'});await page.getByPlaceholder('账号').fill(username);await page.getByPlaceholder('密码').fill(password);await page.locator('button[type=submit]').click();await page.waitForURL('**/overview');
  const response=page.waitForResponse(r=>r.url().includes(`/tasks/${id}/step-assignments`)&&r.status()===200);
  await page.goto('http://127.0.0.1:15179/tasks/'+id,{waitUntil:'networkidle'});ev.api=(await(await response).json()).data;
  await page.locator('[data-testid=task-progress]').waitFor();ev.progressText=await page.locator('[data-testid=task-progress]').innerText();ev.text=await page.locator('body').innerText();
  ev.checks={counts:ev.progressText.includes(`${completed}/${total}`),currentStep:current==='none'?!ev.progressText.includes('当前步骤'):ev.progressText.includes('当前步骤'+current),apiCompletedCount:ev.api.filter(a=>a.stepStatus==='COMPLETED').length===Number(completed),noJsErrors:ev.javascriptErrors.length===0};
  await page.locator('#step-assignments').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(dir,prefix+'.png'),fullPage:true});
 }catch(e){ev.diagnostic=String(e);throw e;}finally{fs.writeFileSync(out,JSON.stringify(ev,null,2));await browser.close();}
 console.log(JSON.stringify(ev.checks));
})().catch(e=>{console.error(String(e));process.exitCode=1;});
