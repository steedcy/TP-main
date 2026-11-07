"""Register the completed V1.180 round without editing product sources or history."""
import csv,io,json,re,shutil,subprocess,hashlib,ast
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3';E=D/'evidence';P='SRS_F023-V1.180-'
def read(name):return json.loads((E/(P+name+'-20261108.json')).read_text(encoding='utf-8-sig'))
def write(name,x):(E/(P+name+'-20261108.json')).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
u=read('ui');ui={x['name']:x for x in u};http=read('http-sql-protocol');clean=read('cleanup-final');allocation=read('allocation-scope');api=read('missing-coordinate-api-auth');service=read('service-coordinate-contract');geo=read('browser-geometry')
def marker(name,device):return next(x for x in ui[name]['markers'] if x['name']==device)
checks={
 'fiveTypesDefaultSelected':len(ui['initial']['checks'])==5 and all(x['checked'] for x in ui['initial']['checks']),
 'mapNatural1260x6895':any(x['naturalWidth']==1260 and x['naturalHeight']==6895 for x in ui['initial']['images']),
 'zoom125':'scale(1.25)' in ui['zoom125']['canvas'],
 'zoomRestores100':'scale(1)' in ui['zoom100']['canvas'],
 'fitAllPreservesAspect':abs(geo['image']['rect']['height']/geo['image']['rect']['width']-6895/1260)<.001,
 'fiveIndependentFilters':[len(ui['filter-'+str(i)]['markers']) for i in range(5)]==[3,0,1,2,6],
 'zeroSelectionHasNoMarkers':len(ui['filter-none']['markers'])==0,
 'panChangesTransform':ui['pan']['canvas']!=ui['zoom100']['canvas'],
 'wheelZoom112':'scale(1.12)' in ui['wheel']['canvas'],
 'offlineGrey':marker('offline-overlap-selected','G180 SMART_DISPLAY')['color']=='rgb(139, 144, 152)',
 'offlineMarkerActuallySelected':'G145_F013_DISPLAY' in ui['offline-overlap-selected']['text'] and '不影响任务' in ui['offline-overlap-selected']['text'],
 'offlineLastTimeRed':any(x['text']=='2026-11-08T00:23:58.612214' and x['color']=='rgb(207, 19, 34)' and x['weight']=='600' for x in ui['offline-overlap-selected']['redTimes']),
 'offlineReasonAndTimeInModal':'离线原因码' in ui['offline-overlap-selected']['text'] and '2026-11-08T00:24:38.020901' in ui['offline-overlap-selected']['text'],
 'selectedInlineZ6':any('z-index: 6' in x['style'] for x in ui['offline-overlap-selected']['markers']),
 'onlineOverlapSelectsRequestedDisplay':ui['048-online-overlap-counterexample']['text'].count('G145_F013_DISPLAY')==2,
 'filteredDisplayLegalControl':ui['recovery-filtered-legal-control']['text'].count('G145_F013_DISPLAY')==2 and '综合信息展示' in ui['recovery-filtered-legal-control']['text'],
 'recoveryRemovesOfflineFields':'离线原因码' not in ui['recovery-filtered-legal-control']['text'],
 'refreshFailurePreservesSix':len(ui['refresh-failed-retains-data']['markers'])==6 and '态势刷新失败' in ui['refresh-failed-retains-data']['text'] and '保留上次成功获取的数据' in ui['refresh-failed-retains-data']['text'],
 'busyOrange':marker('busy-task-details','G180 MOBILE_ROBOT')['color']=='rgb(245, 158, 11)',
 'taskCapabilitiesAndLastReport':'空间引导' in ui['busy-task-details']['text'] and '最后上报' in ui['busy-task-details']['text'] and '任务 1096' in ui['busy-task-details']['text'],
 'actualTaskNavigation':ui['task-detail-loaded']['url'].endswith('/tasks/1096') and 'TASK-20261108-1086' in ui['task-detail-loaded']['text'],
 'completionGreenIdle':marker('task-completed-idle','G180 MOBILE_ROBOT')['color']=='rgb(22, 163, 74)',
 'mapFailureListFallback':'F2.jpg 底图加载失败' in ui['map-failure-settled']['text'] and 'G145_F013_DISPLAY' in ui['map-failure-settled']['text'] and any(x['src']=='/F2.jpg' and x['naturalWidth']==0 for x in ui['map-failure-settled']['images']),
 'activeTaskOfflineImpact':'影响任务 1097（等待异常恢复）' in ui['offline-task-impact']['text'] and 'ERR_HEARTBEAT_TIMEOUT' in ui['offline-task-impact']['text'],
 'invalidCoordinatesListOnly':set(x['name'] for x in ui['coordinate-contract']['markers'])=={'CONTRACT_ORIGIN','CONTRACT_MAX'} and '6 个设备缺少有效坐标' in ui['coordinate-contract']['text'],
 'sixInvalidListRows':all(x in ui['coordinate-contract']['text'] for x in ['CONTRACT_NULL_X','CONTRACT_NULL_Y','CONTRACT_EMPTY','CONTRACT_NEGATIVE','CONTRACT_OVER_X','CONTRACT_OVER_Y']),
 'validOriginAndMax':marker('coordinate-contract','CONTRACT_ORIGIN')['style'].startswith('left: 0%; top: 0%;') and 'left: 100%; top: 100%;' in marker('coordinate-contract','CONTRACT_MAX')['style'],
 'emptyState':len(ui['empty-contract']['markers'])==0 and '当前没有已登记的设备代理' in ui['empty-contract']['text'],
 'automaticLiveRecovery':len(ui['live-restored-automatically']['markers'])==6 and '态势刷新失败' not in ui['live-restored-automatically']['text'] and '底图加载失败' not in ui['live-restored-automatically']['text'],
 'recalibrationNotice':'更换底图尺寸或裁剪范围须重新标定坐标' in ui['final-live-readonly']['text'],
 'noEditorOrCommandControls':all(x not in ui['final-live-readonly']['text'] for x in ['下发指令','地图编辑','轨迹回放','地图版本管理']),
 'pixelCoordinatesProportional':all(abs(x['xRatio']-450/1260)<.00003 and abs(x['yRatio']-260/6895)<.00003 for x in geo['markers'] if x['name'] in ['G180 SMART_DISPLAY','G180 MOBILE_ROBOT']),
 'apiBoundaryAndAuth':all(api['checks'].values()),
 'serviceNullContract':all(service['checks'].values()),
 'currentAllocationsZero':all(allocation['checks'].values()),
 'occupiedAgentsZero':clean['occupiedAgents']=='0',
 'threeTasksTerminal':all(t['status'] in ['MANUAL_TERMINATED','COMPLETED','FAILED'] for t in clean['tasks']),
 'allOwnedDevicesInactive':all(d['deviceStatus']=='INACTIVE' for d in clean['devices']),
 'allOwnedAgentReferencesEmpty':all(a['current_task_id'] is None for a in clean['ownedAgents']),
 'noInjectedTriggers':clean['injectionTriggers']=='0',
 'riskSettingRestored':all(read('risk-fixture-restored')['checks'].values()),
 'productSourcesUnchanged':subprocess.check_output(['git','diff','V1.180','--name-only','--','backend','frontend'],cwd=R,text=True).strip()==''
}
network=next(x for x in http['cases'] if x['name']=='cleanup')['network'];samples=[x for x in network if x['path'].startswith('/api/v1/situation/snapshot')][:20];gaps=[b['startEpoch']-a['startEpoch'] for a,b in zip(samples,samples[1:])]
checks['refresh5sAndUnder15']=len(gaps)>=10 and all(4<gap<6 for gap in gaps)
checks['situationUIReadOnly']=all(x['path']=='/api/v1/auth/login' for x in network if x['method']!='GET')
failureNames=[k for k,v in checks.items() if not v];assert failureNames==['onlineOverlapSelectsRequestedDisplay'],failureNames
write('complete-verification',{'productSha':http['productSha'],'tag':'V1.180','handoffSha':http['handoffSha'],'executionBaseline':'V2.4 / BL-008','timezone':'Asia/Shanghai','decision':'READY_FOR_CLAUDE (repair receiver: Germini per latest user authorization)','ruleCounts':{'P':9,'F':1,'NT':0},'stepCounts':{'P':3,'F':2,'NT':0},'checks':checks,'assertionCounts':{'P':sum(checks.values()),'F':len(checks)-sum(checks.values())},'browserCheckpoints':len(u),'browserCheckpointNote':'29保存点含相同观察的补充/稳定后画面；不作为29次去重业务实测计数。','backendTestReports':464,'backendExecutedPassed':462,'backendSkipped':2,'serviceContractRows':5,'serviceChecks':4,'httpTaskIds':[1095,1096,1097],'taskNote':'1095资源风险前置诊断；1096正式完成与UI链接；1097正式执行中离线影响。无SQL伪造任务生命周期。','refreshSamples':samples,'refreshGapsSeconds':gaps,'networkRequests':len(network),'snapshotRequests':sum('/situation/snapshot' in x['path'] for x in network),'historyReuseCount':0,'legacyPendingRows':allocation['allLegacyPendingRows'],'scopeNote':'历史26待分配状态行均任务ID<1095，未修改；本轮任务活跃分配0，整个库设备占用0。','evidenceFiles':[x.name for x in E.glob(P+'*')],'diagnostics':['启动支持进程早于JAR健康导致连接拒绝，健康UP后重新启动。','新建第二设备触发自有库20登记上限，保留已建G180机器人，复用G145显示和G175航延夹具并保存/恢复配置。','offline采集SQL误用agent_id，实际离线已发生；改device_agent_id并另采事件/SQL，原500仅探针不记产品F。运行进程加载旧函数，后一次offline0亦由外部正确SQL补齐。','1095一候选触发既有RULE_RESOURCE_CRITICAL高风险，未进入承接；保存诊断并终止，仅在GPT schema暂时停用该规则后1096/1097运行，末尾恢复启用/原内容，版本与审计真实递增保留。','一次关闭弹窗时合成快照已自动移除选中对象，定位无匹配；fresh AX后继续。','map-load-failed/task-navigation为加载中的早期画面，settled/detail-loaded补充分层裁决，原图不删除。']})

def update_csv(path,key,updates,snapshot):
 data=path.read_bytes();dest=E/(P+snapshot+'-20261108.csv')
 if not dest.exists():dest.write_bytes(data)
 reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')));fields=reader.fieldnames;items=list(reader)
 for row in items:
  if row[key] in updates:row.update(updates[row[key]])
 out=io.StringIO(newline='');w=csv.DictWriter(out,fields,lineterminator='\n');w.writeheader();w.writerows(items)
 # Preserve original repository UTF-8 (no BOM); avoid whole-file CRLF churn.
 path.write_bytes(out.getvalue().encode('utf8'))
report='acceptance/stage3/SRS_F023-V1.180-整轮独立复测与统一交修.md';index='acceptance/stage3/evidence/'+P+'complete-verification-20261108.json'
ruleUpdates={}
stepsByRule={1:'TC-070.S1;TC-071.S2',2:'TC-070.S1;TC-070.S2',3:'TC-070.S2',4:'TC-070.S2',5:'TC-070.S3',6:'TC-071.S1',7:'TC-071.S1',8:'TC-070.S1',9:'TC-070.S3',10:'TC-070.S3'}
for i in range(1,11):ruleUpdates[f'SRS_F023.R{i:02d}']={'status':'F' if i==2 else 'P','verifiedBy':stepsByRule[i]+'；V1.180当前实测（R07/R09按BL-008分层/条件）','evidence':index+';'+report,'issue':'DEF-S3-048' if i==2 else ''}
update_csv(D/'rules.csv','ruleId',ruleUpdates,'rules-before')
actuals={
 'TC-070.S1':('F','五类默认/逐类筛选、缩放/全图/平移/滚轮、像素比例与状态色当前P；离线终端重叠点选P，但在线同坐标终端连续点选打开机器人，048残留，完整步骤F。'),
 'TC-070.S2':('F','实际任务1096详情链接/能力摘要/末报时间、完成后空闲与19个5秒间隔当前P；正常浮窗通过不能抵销在线重叠选错对象，完整步骤F。'),
 'TC-070.S3':('P','生产态势只读，浏览器201请求仅登录POST，其余GET；无指令/地图编辑/版本/轨迹入口。当前底图1260x6895未替换，像素比例与重标提示实测；R09按BL-008条件义务裁决，不声称未来换图通过。'),
 'TC-071.S1':('P','真实心跳离线保留末位置/时间并灰显，空闲不影响与1097执行任务影响正反/恢复实测；缺X/Y真实HTTP400档案不变、库NOT NULL，实际控制器空坐标契约及真实浏览器6非法/2有效边界快照分层通过（BL-008），不宣称持久空坐标设备E2E。'),
 'TC-071.S2':('P','GPT代理层底图404：占位/失败提示及六设备列表保留；快照503：保留六设备/最近成功更新时间并显示失败时间；恢复live后自动重获数据，map重新加载成功。')}
update_csv(D/'steps.csv','stepId',{k:{'status':v[0],'observedAt':'2026-11-08','actual':'V1.180 / 1c612d55c9e228b2bdbea1375101648060c9dfc7；'+v[1],'evidence':index+';'+report,'issue':'DEF-S3-048' if v[0]=='F' else ''} for k,v in actuals.items()},'steps-before')
issueUpdates={
 'DEF-S3-047':{'状态':'V1.180独立复测关闭（F005历史范围保留；F023当前完成）','事实':'历史事实见原记录及issues-before快照；本版真实心跳超时两分支，灰显末位置/红色加粗末报、ERR_HEARTBEAT_TIMEOUT/离线时间与事件一致。空闲显示不影响任务，1097执行设备显示影响任务1097；恢复后online且offline=null/提示消失，当前关闭。','证据':index+';'+report,'阶段4动作':'保持离线/恢复、有关/无关任务影响及红色时间正反回归。'},
 'NT-S3-024':{'状态':'V1.180按BL-008分层补齐并关闭（原NT保留）','事实':'原NT及注入界面局部P保留。当前真实缺X/缺Y四请求400且档案不变、库NOT NULL；实际控制器保留null X/Y/双null契约通过，生产浏览器合成快照六无效仅列表/0与最大有效边界正确。分层不冒写持久空坐标或真实设备端到端。','证据':index+';acceptance/stage0/F023-防御分支与底图部署条件-V2.4.md','阶段4动作':'未来上游合法引入可空坐标时补真实持久链路回归；维持缺坐标不定位。'}
}
# Keep every historical sentence for 047/024 as well as the archived full before-ledger.
with (D/'issues.csv').open(encoding='utf-8-sig',newline='') as f:
 for row in csv.DictReader(f):
  if row['编号'] in issueUpdates:
   new=issueUpdates[row['编号']];new['事实']=row['事实']+'；2026-11-08追加：'+new['事实'];new['证据']=row['证据']+';'+new['证据']
update_csv(D/'issues.csv','编号',issueUpdates,'issues-before')

summary=f'''# SRS_F023 V1.180 整轮独立复测与统一交修

2026-11-08，Asia/Shanghai，V2.4 / BL-008。**READY_FOR_CLAUDE（修复接收者按用户最新授权为Germini）；整项未通过：规则9P/1F/0NT，步骤3P/2F/0NT。** 全部当前适用项已执行，历史P复用0。没有修改产品代码；main保持dbd7b5c31ede69aedd25023986a89af9c6bf43ce，无本轮合并/PR，不推进F024。

固定产品：`1c612d55c9e228b2bdbea1375101648060c9dfc7` / `V1.180`。Claude交接文档`605de7e4fef9343c74d50d498f293280734320e4`，远端分支/标签解引用实核一致；F022已合main。测试worktree `C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`，分支ai/gpt-test。交接R01～R08/410测试为文字遗漏/旧计数，本轮依正式R01～R10/五步骤及独立464报告执行。ROADMAP暂存047/048实际已纳入产品五文件；不凭交接声明判通过。

| 范围 | 本轮结果 |
| --- | --- |
| R01、R03～R10 | 9P（R07分层防御/R09当前固定底图条件按BL-008） |
| R02 | F：在线重叠标记无法可靠打开目标详情 |
| TC-070.S1/S2 | F；其余完整子观察P不抵销048 |
| TC-070.S3、TC-071.S1/S2 | 3P |
| DEF-S3-047 / NT-S3-024 | 当前关闭，历史失败/NT与原证据保留 |
| DEF-S3-048 | 既有缺陷残留；离线分支P，恢复在线后仍F，沿用编号 |

DEF-S3-048：同一实际快照中，真实HTTP登记/更新且持久的G145_F013_DISPLAY（G180 SMART_DISPLAY）和G180_F023_0（G180 MOBILE_ROBOT）像素坐标均为(450,260)，两者均ENABLED/ONLINE/IDLE。使用真实浏览器按钮定位、真实鼠标点击终端（未force/DOM触发），连续两次实际弹窗均是机器人G180_F023_0；终端在DOM存在但中心被机器人遮住。离线终端层级4高于在线2时可正常点击；恢复后均2，悬停7只会给最上面的命中对象，未解决下层对象选择。筛掉仿真体/机器人后终端正常打开（合法对照）。修复须为同状态/重叠标记提供可靠的目标选择交互，保持离线、忙碌、已选和悬停优先；不能只增加层级常量或依赖先筛选绕过。原故障与本轮反例均留存，无重复编号。首F检查点`169ecd2c`的完整实际SHA见Git日志与正式交接，已推送后继续整轮。

其他实测：五类默认/逐类筛选、0筛选、125%/100%/全图/平移/滚轮；底图natural1260x6895、坐标左上原点与同比例；绿空闲/橙忙碌/灰离线；能力摘要/末报、任务1096真实链接到TASK-20261108-1086、完成后空闲；真实心跳停报/恢复、不影响任务与影响1097正反；图404占位列表、快照503保留数据/失败时间、恢复自动刷新。前20自动快照19间隔{min(gaps):.3f}～{max(gaps):.3f}秒，≤15秒。界面网络201请求/189快照，仅登录POST，其余GET；没有态势下发设备指令。当前控制台采集0错误/警告，故障注入由代理原始状态码单独记录。

BL-008先记录再浏览器合成坐标执行：真实四次缺X/Y编辑400、无持久修改/两列NOT NULL；实际控制器对上游null X/null Y/双null保留（服务5行/4断言）；生产浏览器六无效坐标仅列表（空X、空Y、空串、负数、X越界、Y越界），有效原点/最大边界定位。层级分别标明，不把合成快照称为真实持久设备。R09当前底图未更换，真实尺寸/现有像素比例、只读与重标提示当前检查；未来不同尺寸/裁剪部署仍必须实施方全设备重标再测，不宣称已完成未来换图。

后端独立`mvn -o test`464报告、462执行通过、0失败/错误、2原有跳过；`mvn -o package -DskipTests`、`npm run build`成功；实际打包JAR18129健康UP/认证与关键任务入口运行。现有marker算法自检通过，仅组件层，不替代048 UI验收。3真实HTTP任务1095/1096/1097（1前置风险诊断、2正式业务），未SQL伪造生命周期。29浏览器保存点包含重复/加载后补充画面，不计为29次去重业务执行；总核对{len(checks)}断言，{sum(checks.values())}P/1F，与规则/步骤计数分开。模型受控HTTP、设备协议仿真，无真实硬件或商业模型质量声明。当前F023与直接F005离线/任务入口当前回归，未拿历史P替代；不代表F024以后、三核心或95项整体验收通过。

资源与恢复：GPT schema tip_gpt_f006_v118_20261030 / Redis10；后端18129、模型18117、UI15179、协议18132～18134、控制18135。复用G145/G175并保留原配置，G180为本轮创建；三设备INACTIVE/坐标名称接口原值恢复，定义DISABLED、能力启停原值恢复，规则RESOURCE_CRITICAL启用/原内容恢复，真实版本/审计递增不回滚。3任务终态；本轮活跃分配0、全库代理占用0、注入触发器0。全库26旧PENDING_ASSIGNMENT/EXECUTING状态行均taskId<1095（7待人工/19历史终止），逐行索引单列，未改历史任务；不能把全库26直接写成本轮遗留。失败任务、版本和证据保留。确认命令归属后停止2自有进程/七端口无监听，未动共享PostgreSQL/Redis或Claude资源。主工作区用户文件未写入/未同步main。

环境与探针更正详见complete-verification diagnostics：支持进程早启动、20登记上限、offline SQL列名、资源风险前置、弹窗被刷新移除及早期加载画面；均自行修正/补证，不当产品缺陷。原图/原记录保留，产品源码与V1.180差异为空。原始Office、令牌/DPAPI/JAR/私有环境不入提交。

证据入口：`{index}`；HTTP/SQL/protocol、offline-correction/offline-active-task、missing-coordinate-api-auth、service-coordinate-contract、ui/29截图、browser-geometry、allocation-scope、cleanup-final/process-cleanup、构建/测试日志均在同目录。可重跑夹具`probe-f023-v180-runtime.py`，独立服务探针`F023SnapshotContractProbe.java`。先推完整证据，再由GPT单写HANDOFF/ROADMAP并记录实际证据SHA。最新用户指令：后续由Germini修复，修复/复测分别独立对话；F027/F028复用既有预修复对话，到项先核查归并，不重复修复；修复轮10分钟检查工作状态/提交。
'''
(D/Path(report).name).write_text(summary,encoding='utf8')
progress=D/'阶段3-复测进度.md';text=progress.read_text(encoding='utf8');intro='\n\n- **2026-11-08 / F023 V1.180 / V2.4：READY_FOR_CLAUDE（实际接收Germini），9P/1F/0NT，五步骤3P/2F/0NT**。047及024（BL-008分层）当前关闭，048离线P/在线重叠点选仍F；全部当前适用项完成，历史P复用0。464报告462执行通过2跳过、生产构建/实际JAR/三任务/29 UI保存点；自有配置恢复、当前活跃分配0/代理占用0，历史26状态行单列保留。完整报告`SRS_F023-V1.180-整轮独立复测与统一交修.md`，证据先推后正式交接；main保持dbd7b5c，无合并/PR，不推进下一需求。\n'
progress.write_text(text.split('\n',1)[0]+intro+text.split('\n',1)[1],encoding='utf8')
print('Registered F023:',len(checks),'assertions;',len(u),'browser checkpoints;',failureNames)
