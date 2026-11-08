"""V1.182 independent full-round registration. Does not change product sources."""
import csv,io,json,re,subprocess,hashlib,ast
from datetime import datetime
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3';E=D/'evidence';P='SRS_F023-V1.182-'
def read(n):return json.loads((E/(P+n+'-20261108.json')).read_text(encoding='utf-8-sig'))
def write(n,x):(E/(P+n+'-20261108.json')).write_bytes(json.dumps(x,ensure_ascii=False,indent=2).encode('utf8'))
uiRows=read('ui');u={x['name']:x for x in uiRows};h=read('http-sql-protocol');clean=read('cleanup-final');api=read('api-boundary-auth');service=read('service-coordinate-contract');version=read('version-alignment')
def dialog(n):return '\n'.join(u[n]['dialogs'])
def marker(n,name):return next(x for x in u[n]['markers'] if x['name']==name)
def updated(n):return re.search(r'最近更新：[ \t]*([^\n]+)',u[n]['text']).group(1).strip()
def ratio_ok(n):
 c=u[n]['canvasRect']
 for x in u[n]['markers']:
  rx=x['rect'];left=float(re.search(r'left: ([\d.]+)%',x['style']).group(1))/100;top=float(re.search(r'top: ([\d.]+)%',x['style']).group(1))/100
  if abs((rx['left']+rx['width']/2-c['left'])/c['width']-left)>.00003 or abs((rx['top']+rx['height']/2-c['top'])/c['height']-top)>.00003:return False
 return True
checks={
 'defaultFiveSelected':len(u['initial']['filters'])==5 and all(x['checked'] for x in u['initial']['filters']),
 'naturalMap1260x6895':any(x['naturalWidth']==1260 and x['naturalHeight']==6895 for x in u['initial']['images']),
 'sameCoordinateChooserHasBothIdentities':all(x in dialog('same-coordinate-chooser') for x in ['G145_F013_DISPLAY','G180_F023_0','智慧航显','移动服务机器人','综合信息展示','空间引导']),
 'requestedDisplaySelected':'设备编码\tG145_F013_DISPLAY' in dialog('same-coordinate-display-selected'),
 'switchRobot':'设备编码\tG180_F023_0' in dialog('peer-switch-robot'),
 'switchDisplay':'设备编码\tG145_F013_DISPLAY' in dialog('peer-switch-display'),
 'nearCoordinateChooser':all(x in dialog('near-coordinate-chooser') for x in ['X 450, Y 260','G145_F013_DISPLAY','G180_F023_0']),
 'nearCoordinateCorrectIdentity':'设备编码\tG145_F013_DISPLAY' in dialog('near-coordinate-display-selected') and 'X 440, Y 260' in dialog('near-coordinate-display-selected'),
 'singleDirectHasNoPeerSelector':'设备编码\tG175_F022_FLIGHT' in dialog('single-direct-selected') and '同坐标重叠设备' not in dialog('single-direct-selected'),
 'offlinePriorityDirect':'设备编码\tG180_F023_0' in dialog('offline-priority-direct') and '离线原因码' in dialog('offline-priority-direct'),
 'mixedStatusPeerSwitch':'设备编码\tG145_F013_DISPLAY' in dialog('mixed-status-peer-switch') and '切换至 G182 MOBILE_ROBOT（离线）' in dialog('mixed-status-peer-switch'),
 'chooserLatestOfflineWithin15s':all(x in dialog('chooser-after-offline') for x in ['G182 SMART_DISPLAY离线','ERR_HEARTBEAT_TIMEOUT','不影响任务']) and 'G182 SMART_DISPLAY在线' not in dialog('chooser-after-offline'),
 'chooserMembersUpdatedAfterMove':'G145_F013_DISPLAY' not in dialog('chooser-after-position-change') and 'G180_F023_0' in dialog('chooser-after-position-change') and '存在 1 个' in dialog('chooser-after-position-change'),
 'normalDetailRefreshesOffline':'在线/工作状态\t离线' in dialog('offline-active-task-impact') and 'ERR_HEARTBEAT_TIMEOUT' in dialog('offline-active-task-impact'),
 'normalDetailRecovers':'在线/工作状态\t在线·忙碌' in dialog('active-task-recovered-details') and '离线原因码' not in dialog('active-task-recovered-details'),
 'offlineGray':marker('offline-priority-direct','G182 MOBILE_ROBOT')['color']=='rgb(139, 144, 152)',
 'offlineLastReportRed':any(x['color']=='rgb(207, 19, 34)' and x['weight']=='600' for x in u['offline-priority-direct']['redTimes']),
 'idleNoTaskImpact':'不影响任务' in dialog('chooser-after-offline'),
 'zoom125':'scale(1.25)' in u['zoom125']['canvas'],
 'zoom100':'scale(1)' in u['zoom100']['canvas'],
 'fitAllAspect':abs(u['fitall']['canvasRect']['height']/u['fitall']['canvasRect']['width']-6895/1260)<.001,
 'pixelGeometryAtAllThreeScales':all(ratio_ok(n) for n in ['initial','zoom125','fitall','zoom-out-button']),
 'panChangesTransform':all(abs(b-a-d)<.01 for a,b,d in zip(map(float,re.search(r'translate\(([-\d.]+)px, ([-\d.]+)px\)',u['fitall']['canvas']).groups()),map(float,re.search(r'translate\(([-\d.]+)px, ([-\d.]+)px\)',u['pan']['canvas']).groups()),[70,30])) and re.search(r'scale\(([^)]+)\)',u['pan']['canvas']).group(1)==re.search(r'scale\(([^)]+)\)',u['fitall']['canvas']).group(1),
 'wheel112':'scale(1.12)' in u['wheel']['canvas'],
 'fiveFilterBranches':[len(u['filter-'+str(i)]['markers']) for i in range(5)]==[3,0,1,2,6],
 'emptyTypeSelection':len(u['filter-none']['markers'])==0,
 'busyOrange':marker('busy-task-details','G182 MOBILE_ROBOT')['color']=='rgb(245, 158, 11)',
 'busyTaskSummary':'任务 1100' in dialog('busy-task-details') and '空间引导' in dialog('busy-task-details') and '最后上报' in dialog('busy-task-details'),
 'busyPeerSwitchBothDirections':'设备编码\tG145_F013_DISPLAY' in dialog('busy-peer-switch-display') and '设备编码\tG180_F023_0' in dialog('busy-peer-switch-robot') and '任务 1100' in dialog('busy-peer-switch-robot'),
 'actualTaskNavigation':u['actual-task-navigation']['url'].endswith('/tasks/1100') and 'F182 synthetic navigation F2_TEST_GATE' in u['actual-task-navigation']['text'],
 'refreshFailureRetainsSix':len(u['refresh-failed']['markers'])==6 and '态势刷新失败' in u['refresh-failed']['text'] and '保留上次成功获取的数据' in u['refresh-failed']['text'],
 'retryKeepsLastSuccessTime':updated('refresh-failed')==updated('refresh-retry-retains-data'),
 'automaticRecoveryIdle':len(u['automatic-recovery-completed-idle']['markers'])==6 and '态势刷新失败' not in u['automatic-recovery-completed-idle']['text'] and marker('automatic-recovery-completed-idle','G182 MOBILE_ROBOT')['class'].endswith('marker-online'),
 'mapFailureFallback':len(u['map-failure-list-retained']['markers'])==6 and 'F2.jpg 底图加载失败' in u['map-failure-list-retained']['text'] and 'G145_F013_DISPLAY' in u['map-failure-list-retained']['text'] and any(x['src']=='/F2.jpg' and x['naturalWidth']==0 for x in u['map-failure-list-retained']['images']),
 'eightInvalidOnlyInList':len(u['coordinate-contract-eight-invalid']['markers'])==2 and all(x in u['coordinate-contract-eight-invalid']['text'] for x in ['NULL_X','NULL_Y','BOTH_NULL','NAN','EMPTY','NEGATIVE','OVER_X','OVER_Y']) and '8 个设备缺少有效坐标' in u['coordinate-contract-eight-invalid']['text'],
 'validOriginAndMax':set(x['name'] for x in u['coordinate-contract-eight-invalid']['markers'])=={'CONTRACT_ORIGIN','CONTRACT_MAX'} and 'left: 100%; top: 100%;' in marker('coordinate-contract-eight-invalid','CONTRACT_MAX')['style'],
 'emptySnapshot':not u['empty-contract']['markers'] and '当前没有已登记的设备代理' in u['empty-contract']['text'],
 'activeTaskOfflineImpact':'影响任务 1101（等待异常恢复）' in dialog('offline-active-task-impact') and 'ERR_HEARTBEAT_TIMEOUT' in dialog('offline-active-task-impact'),
 'activeDetailRecovers':'在线/工作状态\t在线·忙碌' in dialog('active-task-recovered-details') and '离线原因码' not in dialog('active-task-recovered-details'),
 'recalibrationNotice':'更换底图尺寸或裁剪范围须重新标定坐标' in u['final-readonly']['text'],
 'noEditorCommandEntry':all(x not in u['final-readonly']['text'] for x in ['下发指令','地图编辑','地图版本管理','轨迹回放']),
 'httpBoundaryAuth':all(api['checks'].values()),
 'currentServiceNullContract':all(service['checks'].values()),
 'allCurrentProtocolCasesPass':all(x.get('result','P')=='P' for x in h['cases']),
 'cleanupAllChecksPass':all(clean['checks'].values()),
 'allProductSourcesUnchangedByGPT':subprocess.check_output(['git','diff','V1.182','--name-only','--','backend','frontend'],cwd=R,text=True).strip()=='',
 'portsReleased':not read('process-cleanup')['listenersAfter']
}
net=h['cases'][-1]['network'];samples=[x for x in net if '/situation/snapshot' in x['path']][:20];gaps=[b['startEpoch']-a['startEpoch'] for a,b in zip(samples,samples[1:])];checks['automaticHttp5s']=len(gaps)==19 and all(4<x<6 for x in gaps);checks['uiNetworkReadOnly']=all(x['path']=='/api/v1/auth/login' for x in net if x['method']!='GET')

from datetime import timezone,timedelta
TZ=timezone(timedelta(hours=8))

def dt(t):
 d=datetime.fromisoformat(t.replace('Z','+00:00'))
 return d if d.tzinfo else d.replace(tzinfo=TZ)
timeout=next(c for c in h['cases'] if c['name']=='heartbeat-timeout-1')
offlineAt=next(a['offline']['offlineAt'] for a in timeout['after']['agents'] if a['deviceCode']=='G145_F013_DISPLAY')
move=next(c for c in h['cases'] if c['name']=='position-100')
latencies={'offlineWindowSeconds':(dt(u['chooser-after-offline']['at'])-dt(offlineAt)).total_seconds(),'moveWindowSeconds':(dt(u['chooser-after-position-change']['at'])-dt(move['at'])).total_seconds()}
checks.update({
 'offlineObservedWithin15s':0<=latencies['offlineWindowSeconds']<=15,
 'moveObservedWithin15s':0<=latencies['moveWindowSeconds']<=15,
 'chooserRecovery':'G182 SMART_DISPLAY在线·空闲' in dialog('chooser-after-recovery') and '离线原因' not in dialog('chooser-after-recovery'),
 'newMemberJoined':all(c in dialog('chooser-member-joined') for c in ['G175_F022_FLIGHT','G180_F023_0']) and 'G145_F013_DISPLAY' not in dialog('chooser-member-joined'),
 'originalClickedDeviceMoved':'G180_F023_0' not in dialog('chooser-original-device-moved') and 'G175_F022_FLIGHT' in dialog('chooser-original-device-moved'),
 'latestMemberIdentity':'设备编码\tG175_F022_FLIGHT' in dialog('chooser-latest-member-selected'),
 'capabilitySnapshotContract':'已启用能力：航班变更信息发布' in dialog('chooser-capabilities-contract') and '综合信息展示' not in dialog('chooser-capabilities-contract'),
 'removedMembersContract':'存在 0 个' in dialog('chooser-all-members-removed-contract') and all(c not in dialog('chooser-all-members-removed-contract') for c in ['G145_F013_DISPLAY','G180_F023_0']),
 'contractRecovery':'综合信息展示' in dialog('chooser-contract-live-recovery') and all(c in dialog('chooser-contract-live-recovery') for c in ['G145_F013_DISPLAY','G180_F023_0']),
 'zoomOutButton':'scale(0.8)' in u['zoom-out-button']['canvas'],
 'taskCompletionPersisted':next(c for c in h['cases'] if c['name']=='core-task-completion')['task']['status']=='COMPLETED'
})
failed=[k for k,v in checks.items() if not v]
write('verification-draft',{'checks':checks,'failed':failed,'latencies':latencies,'uiFrames':len(uiRows),'networkRequests':len(net),'refreshGaps':gaps})
print('verification',len(checks),'assertions; failed',failed,'latencies',latencies)
assert not failed,failed

# Register only after the complete current-version observation set and cleanup pass.
assert all(read('definition-cleanup')['checks'].values())
index='acceptance/stage3/evidence/'+P+'complete-verification-20261108.json'
report='acceptance/stage3/SRS_F023-V1.182-整轮独立复测与验收.md'
meta={'tag':'V1.182','productSha':version['productSha'],'handoffSha':version['handoffSha'],'timezone':'Asia/Shanghai','executionBaseline':'V2.4 / BL-008 unchanged','decision':'REQUIREMENT_PASSED','rules':{'P':10,'F':0,'NT':0},'steps':{'P':5,'F':0,'NT':0},'checks':checks,'assertions':{'P':len(checks),'F':0},'latencies':latencies,'closedCurrent':'DEF-S3-118','stillClosed':['DEF-S3-047','DEF-S3-048','NT-S3-024'],'uiSavedCheckpoints':len(uiRows),'protocolCaseRecords':len(h['cases']),'networkRequests':len(net),'snapshotRequests':sum('/situation/snapshot' in x['path'] for x in net),'refreshSamples':samples,'refreshGapsSeconds':gaps,'tasks':clean['tasks'],'historicalBusinessCoverageUsed':0,'historicalComponentCoverage':{'tag':'V1.180','sha':'1c612d55c9e228b2bdbea1375101648060c9dfc7','backendTree':'7a6b7eeec6684ab95cefffc6ffc981b83358ed8e','reports':464,'executedPassed':462,'originalSkipped':2,'reason':'Complete backend/pom tree identical in V180/V181/V182. Production JAR reused; actual fresh current JAR health/HTTP/SQL/protocol/controller contract and UI tested. No claim of current full backend unit rerun.','jarSha256':version['backendArtifactSha256']},'mainAtTestCompletion':'dbd7b5c31ede69aedd25023986a89af9c6bf43ce','mainMerge':'Pending separately verified safe main synchronization after evidence and formal handoff push.','limitations':['Protocol synthetic adapters and controlled model; no physical-device or commercial model-quality claim.','BL008 null-coordinate tests are HTTP rejection/controller DTO/production renderer contract layers; not persisted nullable-device E2E.','Fixed 1260x6895 map unchanged; future changed dimensions/crop still requires full device recalibration and new acceptance.','No separately executed hover action claimed; current algorithm check and CSS inspection are separate evidence layers.'],'diagnostics':['String-code-generation helper attempt was disallowed; capture function explicitly defined instead. No product behavior changed.','One initial read omitted explicit UTF8 and failed decoding; corrected UTF8 read, raw artifact unchanged.','Task link worked; guessed task-detail heading was absent. Fresh DOM confirmed actual /tasks/1100 and correct goal, no product failure.','Supplemental zoom-out click executed once. Capture closure referenced closed tab4; fresh tab5 binding captured existing80% result without repeated click.','Read-only cleanup SQL first used d.status; corrected to actual d.device_status. No mutation or product defect.','Pan verifier initially asserted absolute70,30; actual fitall already translated441.911,0. Corrected delta comparison verifies511.911,30 minus441.911,0 equals70,30 with unchanged scale. Original raw frames preserved.','Frontend build passed39.88s with existing large-chunk warning; handoff0warning statement was not adopted.']}
write('complete-verification',meta)
write('probe-diagnostics',{'at':datetime.now().astimezone().isoformat(),'tag':'V1.182','diagnostics':meta['diagnostics'],'panOriginalFailedProbeAssertion':"'translate(70px, 30px)' in pan.canvas",'panActualBefore':u['fitall']['canvas'],'panActualAfter':u['pan']['canvas'],'classification':'probe expectation error corrected; not product F'})

def update(name,key,changes):
 path=D/(name+'.csv');before=path.read_bytes();backup=E/(P+name+'-before-20261108.csv')
 if not backup.exists():backup.write_bytes(before)
 reader=csv.DictReader(io.StringIO(before.decode('utf-8-sig')));fields=reader.fieldnames;items=list(reader)
 for row in items:
  if row[key] in changes:row.update(changes[row[key]])
 out=io.StringIO();writer=csv.DictWriter(out,fields,lineterminator='\n');writer.writeheader();writer.writerows(items);path.write_bytes(out.getvalue().encode('utf8'))

ruleDetails={1:'最新位置/名称/在线与忙碌状态、候选窗口状态/位置/成员当前同步通过；118关闭。',2:'1100真实任务详情、能力/末报摘要、正确任务路由和普通详情刷新通过。',3:'首20自动snapshot的19间隔约5秒；候选与普通详情真实状态当前同步，网络观察与UI观察分别记录。',4:f'候选原反例离线{latencies["offlineWindowSeconds"]:.3f}秒、位置移离{latencies["moveWindowSeconds"]:.3f}秒内实见同步；当前观察均未超过15秒。',5:'只读入口/当前浏览器网络，无编辑/版本/标定/轨迹回放。',6:'空闲终端及执行机器人真实心跳离线/恢复，末位置保留、灰色/红时间与任务影响正反通过。',7:'BL008真实HTTP四次缺坐标400/无修改、真实控制器null DTO及生产浏览器八无效/两有效边界分层通过。',8:'原点/最大像素、1260x6895原比例、125%/100%/全图/80%缩小几何、拖动/滚轮通过。',9:'BL008本版固定底图未替换，资源真实尺寸/几何/重标提示通过；未来换尺寸裁剪仍须全设备重标另验。',10:'真实浏览器除登录POST外全GET，无设备指令入口。'}
update('rules','ruleId',{f'SRS_F023.R{i:02d}':{'status':'P','verifiedBy':'V1.182当前整轮实测；'+ruleDetails[i],'evidence':index+';'+report,'issue':''} for i in range(1,11)})
stepDetails={'TC-070.S1':'五类型默认/逐类/无选、原坐标比例、颜色、放大/缩小/全图/平移/滚轮；048同/近坐标选择、双向/跨层级切换通过。','TC-070.S2':'118原离线与移离反例、在线恢复/新成员/原设备移离/稳定身份，以及分层能力和成员消失契约通过；1100任务链接/真实完成、1101执行中离线及恢复、5秒刷新/15秒边界通过。','TC-070.S3':'无指令/编辑/地图版本/轨迹入口，浏览器只读；固定底图部署条件按BL008通过，不宣称未来换图验收。','TC-071.S1':'真实两设备心跳超时保留末位置、灰色/红色时间与任务影响正反；真实必填拒绝/无改、控制器null DTO、生产UI无效/有效坐标防御分层通过。','TC-071.S2':'底图404占位和六设备列表、快照503及重试保留数据/成功时间、live自动恢复、空快照/恢复通过。'}
update('steps','stepId',{k:{'status':'P','observedAt':'2026-11-08','actual':'V1.182 / '+version['productSha']+'；'+v,'evidence':index+';'+report,'issue':''} for k,v in stepDetails.items()})
issueChanges={}
for row in csv.DictReader((D/'issues.csv').open(encoding='utf-8-sig',newline='')):
 ident=row['编号']
 if ident in ['DEF-S3-047','DEF-S3-048','NT-S3-024','DEF-S3-118']:
  fact={'DEF-S3-047':'V1.182真实空闲/执行离线、原因/时刻/红色末报及任务影响正反当前通过，保持关闭。','DEF-S3-048':'V1.182同/近坐标候选精确选择、双向peer、忙碌/离线优先、非重叠直达当前通过，保持关闭。','NT-S3-024':'V1.182 BL008真实HTTP/控制器/生产UI坐标防御分层当前通过，历史NT保留。','DEF-S3-118':f'V1.182当前原反例A候选离线{latencies["offlineWindowSeconds"]:.3f}秒内显示离线及原因，B移离{latencies["moveWindowSeconds"]:.3f}秒内移除成员；同窗恢复、新成员加入、原点击设备移离、稳定身份/能力/全部消失及合法对照通过，关闭。'}[ident]
  stamp='2026-11-08追加V1.182：'+fact
  issueChanges[ident]={'状态':'V1.182独立整轮复测关闭（历史F/NT保留）' if ident=='DEF-S3-118' else 'V1.182当前复核保持关闭','事实':row['事实'] if stamp in row['事实'] else row['事实']+'；'+stamp,'证据':row['证据'] if index in row['证据'] else row['证据']+';'+index+';'+report}
update('issues','编号',issueChanges)

summary=f'''# SRS_F023 V1.182 整轮独立复测与验收

2026-11-08 Asia/Shanghai，V2.4 / BL-008不变。**REQUIREMENT_PASSED：规则10P/0F/0NT，五步骤5P/0F/0NT。** 全部当前业务范围实测，历史业务P替代0；DEF-S3-118本轮关闭，047/048/NT024保持关闭，历史F/NT及反例全部保留。本报告完成时main仍dbd7b5c31ede69aedd25023986a89af9c6bf43ce；先推证据及正式交接，再独立核实安全同步main，不预报已合并或已推送。F023通过不等于后续需求、三核心场景或95项整体验收通过。

固定产品`5745d6279afac0149e2c614088734dbb2272211a` / `V1.182`；修复方正式交接`b8c2072ac1632c49ba7e98218efe38347f62bc0e`，远端标签/分支核对后GPT独立ai/gpt-test worktree快进接收。本轮产品改动仅SituationView.vue及marker检查脚本；GPT未修改backend/frontend产品源码。暂存efe0790已在V1.180实际纳入，不重复移植；本轮实际功能观察确认047/048仍关闭。

## 原缺陷与当前实测

118反例A：候选保持打开，G145_F013_DISPLAY真实协议停心跳，offlineAt={offlineAt}；生产UI在{latencies['offlineWindowSeconds']:.3f}秒内已显示离线、ERR_HEARTBEAT_TIMEOUT及不影响任务；恢复真实心跳后同窗口自动恢复在线。反例B：该终端从(450,260)真实上报移至(100,800)，{latencies['moveWindowSeconds']:.3f}秒内原候选移除终端，只保留机器人。不是关窗重开或手动刷新后才正确。

继续当前真实协议独立分支：航延屏移入后自动加入候选；最初点击的机器人自身移离后原物理位置仅留下航延屏；点击新成员准确打开其身份。生产UI受控snapshot另验能力更新、两成员全部消失无幽灵候选以及live恢复，不冒写持久设备能力修改或物理设备E2E。048同坐标/近坐标选终端、双向切换、忙碌及离线优先、混合状态peer、单设备直达本轮通过。

R01～R10及TC070S1/S2/S3、TC071S1/S2当前全部P。五类默认/逐类/无选，1260x6895天然底图/像素锚点、125%/100%/全图/80%缩小、真实鼠标拖动70/30增量与滚轮112%均当前通过。普通详情真实任务1100摘要/能力/末报、实际链接/tasks/1100、真实业务指令和反馈形成COMPLETED；1101执行中真实离线显示影响任务1101/离线原因/时刻，灰色末位置/红色末报，普通详情保持打开自动恢复，最后人工终止释放。设备为协议合成、模型受控，不扩大为真硬件或模型质量证明。

刷新503/重试保留六设备及最近成功时间，live自动恢复显示已完成设备空闲；地图404占位/失败说明/列表保留；空快照及恢复通过。浏览器代理{len(net)}请求，其中snapshot{meta['snapshotRequests']}次，除登录POST外全GET；首20自动样本的19间隔{min(gaps):.3f}～{max(gaps):.3f}秒。当前候选和普通详情真实状态同步，与网络定时证据分开证明。

BL008未变：四次真实缺X/Y HTTP400/3001且配置不变；实际控制器5行/4断言保留null；生产UI受控快照八无效仅列表、原点/最大边界合法标记，不宣称持久空坐标设备E2E。固定底图未替换，R09只证明当前资源、几何和重标提示/只读；未来尺寸或裁剪变更仍须全设备重标另验。

## 构建、证据及清理

当前独立前端生产build39.88秒成功，保留既有大chunk提示，不采用修复方0warning描述；当前marker自检和实际控制器契约通过。后端完整树含pom在V1.180/V1.181/V1.182均为7a6b7eeec6684ab95cefffc6ffc981b83358ed8e，明确复用V1.180/1c612d55c9e228b2bdbea1375101648060c9dfc7的464组件报告（462执行通过/2原跳过）及同源码JAR，当前重新实际启动健康UP、HTTP/SQL/协议/控制器/UI全部当前实测，不冒写本轮全量后端单测或后端重新打包。

本轮{len(uiRows)}浏览器保存点、{len(h['cases'])}协议/HTTP记录（含清理）、{len(checks)}核对断言全P；保存点不当作独立业务次数。总索引`{index}`，原图/UI JSON、HTTP SQL protocol、API auth、service coordinate、version alignment、build/marker、cleanup/definition/process、CSV原快照和SHA256清单同目录。可重跑runtime/boundary/audit、Java契约及CUA采证helper均提交。工具/探针诊断详见probe-diagnostics：任务页heading误假设、采证旧tab闭包、SQL列名与全图平移绝对值断言均由GPT修正，不登记产品F；原始正确行为数据保留。未独立执行的悬停不写UI P。

自有schema tip_gpt_f006_v118_20261030 / Redis10、七端口18129/18117/15179/18132～18135；三设备INACTIVE/代理DISABLED、定义DISABLED，原配置/能力启停及RESOURCE_CRITICAL内容与启用恢复，真实版本审计保留。1100 COMPLETED、1101 MANUAL_TERMINATED，本轮分配0/全库代理占用0/注入触发器0，26历史分配行逐项前后相同。确认命令归属后停止Java12508/Python10508，七端口无监听；保留历史任务/版本/证据，不触碰其他资源或用户文件。

按顺序先提交并推本证据，再GPT单写HANDOFF/ROADMAP/EXECUTION_BASELINE，记录实际证据SHA；整项通过后安全同步main并核对远端、用户文件哈希及标签不移动，再按用户授权创建F024独立修复对话，先核查归并既有/暂存332e250内容。F027/F028仍复用原有预修复对话，到项直接核查和提交，当前不提前推进。
'''
(D/Path(report).name).write_bytes(summary.encode('utf8'))
progress=D/'阶段3-复测进度.md';text=progress.read_text(encoding='utf8');stamp='2026-11-08 / F023 V1.182 / V2.4：REQUIREMENT_PASSED'
if stamp not in text:
 first,tail=text.split('\n',1);text=first+'\n\n- **'+stamp+'：规则10P/0F/0NT、步骤5P/0F/0NT**。118两原反例及独立成员分支当前关闭，047/048/024保持；业务历史P替代0，未变后台组件历史报告明确分层。51 UI保存点、两真实任务、生产构建/JAR/HTTP/SQL/协议/坐标契约与清理通过，先推证据及正式交接再核对main安全同步。报告`SRS_F023-V1.182-整轮独立复测与验收.md`。\n'+tail;progress.write_bytes(text.encode('utf8'))
print('Registered REQUIREMENT_PASSED rules10P steps5P; main synchronization still pending.')
