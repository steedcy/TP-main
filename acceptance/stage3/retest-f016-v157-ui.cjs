// Real Edge DOM, API-backed page; never mock page data or persist credentials.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),dir=path.join(__dirname,'evidence');
const {chromium}=require(path.join(root,'../tip/.local-test/node_modules/playwright-core'));
const accounts=Object.fromEntries(fs.readFileSync(path.join(root,'../tip/user.md'),'utf8').split(/\r?\n/).filter(x=>/^\|运行操作员\|/.test(x)).map(x=>{const[,role,username,password]=x.split('|').map(v=>v.trim());return[role,{username,password}]}));
async function main(){
 const out=path.join(dir,'SRS_F016-V1.157-ui-20261105.json');if(fs.existsSync(out))throw Error('Do not overwrite evidence');
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1600,height:1100}}),page=await context.newPage();page.setDefaultTimeout(25000);
 const ev={tag:'V1.157',productSha:'ea6901eb4e35448ca91773f8ea1424fa797d88e5',baseline:'V2.4',at:new Date().toISOString(),timezone:'Asia/Shanghai',browser:browser.version(),javascriptErrors:[],pages:[]};
 page.on('pageerror',e=>ev.javascriptErrors.push(String(e)));
 try{
  await page.goto('http://127.0.0.1:15179/login',{waitUntil:'networkidle'});await page.getByPlaceholder('账号').fill(accounts['运行操作员'].username);await page.getByPlaceholder('密码').fill(accounts['运行操作员'].password);await page.locator('button[type=submit]').click();await page.waitForURL('**/overview');
  for(const [name,id] of [['accepted',299],['rejected-next',307]]){
   await page.goto('http://127.0.0.1:15179/tasks/'+id,{waitUntil:'networkidle'});await page.locator('#step-assignments').waitFor();
   const text=await page.locator('body').innerText(),assignmentText=await page.locator('#step-assignments').innerText();
   await page.locator('#step-assignments').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(dir,`SRS_F016-V1.157-ui-${name}-20261105.png`),fullPage:true});
   ev.pages.push({name,taskId:id,text,assignmentText,checks:{assignmentDeviceAndStateVisible:assignmentText.includes('AGT-')&&assignmentText.includes('已完成'),rankingVisible:text.includes('匹配度')&&text.includes('距离')&&text.includes('负载'),responseTimeVisible:/响应时[间长]|承接耗时|承接响应时间/.test(text),rejectionReasonVisible:name!=='rejected-next'||text.includes('SYNTHETIC_CAPACITY_REJECTED')}});
  }
 }finally{fs.writeFileSync(out,JSON.stringify(ev,null,2)+'\n');await browser.close();}
 console.log(JSON.stringify(ev.pages.map(x=>({name:x.name,checks:x.checks})),null,2));
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
