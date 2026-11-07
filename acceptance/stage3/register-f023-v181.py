"""V1.181 independent full-round registration. Does not change product sources."""
import csv,io,json,re,subprocess,hashlib,ast
from datetime import datetime
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3';E=D/'evidence';P='SRS_F023-V1.181-'
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
 'nearCoordinateChooser':all(x in dialog('near-coordinate-chooser') for x in ['X 440, Y 260','G145_F013_DISPLAY','G180_F023_0']),
 'nearCoordinateCorrectIdentity':'设备编码\tG145_F013_DISPLAY' in dialog('near-coordinate-display-selected') and 'X 440, Y 260' in dialog('near-coordinate-display-selected'),
 'singleDirectHasNoPeerSelector':'设备编码\tG145_F013_DISPLAY' in dialog('single-direct-selected') and '同坐标重叠设备' not in dialog('single-direct-selected'),
 'offlinePriorityDirect':'设备编码\tG145_F013_DISPLAY' in dialog('offline-direct-selected') and '离线原因码' in dialog('offline-direct-selected'),
 'mixedStatusPeerSwitch':'设备编码\tG180_F023_0' in dialog('mixed-status-peer-switch') and '切换至 G181 SMART_DISPLAY（离线）' in dialog('mixed-status-peer-switch'),
 'chooserLatestOfflineWithin15s':u['chooser-after-offline']['checks']['chooserShowsLatestOffline'],
 'chooserMembersUpdatedAfterMove':u['chooser-after-position-change']['checks']['movedDeviceRemovedFromOverlap'],
 'normalDetailRefreshesOffline':'在线/工作状态\t离线' in dialog('offline-details-current') and 'ERR_HEARTBEAT_TIMEOUT' in dialog('offline-details-current'),
 'normalDetailRecovers':'在线/工作状态\t在线·空闲' in dialog('recovered-details') and '离线原因码' not in dialog('recovered-details'),
 'offlineGray':marker('offline-direct-selected','G181 SMART_DISPLAY')['color']=='rgb(139, 144, 152)',
 'offlineLastReportRed':any(x['color']=='rgb(207, 19, 34)' and x['weight']=='600' for x in u['offline-direct-selected']['redTimes']),
 'idleNoTaskImpact':'不影响任务' in dialog('offline-direct-selected'),
 'zoom125':'scale(1.25)' in u['zoom125']['canvas'],
 'zoom100':'scale(1)' in u['zoom100']['canvas'],
 'fitAllAspect':abs(u['fitall']['canvasRect']['height']/u['fitall']['canvasRect']['width']-6895/1260)<.001,
 'pixelGeometryAtAllThreeScales':all(ratio_ok(n) for n in ['initial','zoom125','fitall']),
 'panChangesTransform':u['pan']['canvas']!=u['zoom100']['canvas'],
 'wheel112':'scale(1.12)' in u['wheel']['canvas'],
 'fiveFilterBranches':[len(u['filter-'+str(i)]['markers']) for i in range(5)]==[3,0,1,2,6],
 'emptyTypeSelection':len(u['filter-none']['markers'])==0,
 'busyOrange':marker('busy-task-details','G181 MOBILE_ROBOT')['color']=='rgb(245, 158, 11)',
 'busyTaskSummary':'任务 1098' in dialog('busy-task-details') and '空间引导' in dialog('busy-task-details') and '最后上报' in dialog('busy-task-details'),
 'busyPeerSwitchBothDirections':'设备编码\tG145_F013_DISPLAY' in dialog('busy-peer-switch-display') and '设备编码\tG180_F023_0' in dialog('busy-peer-switch-robot') and '任务 1098' in dialog('busy-peer-switch-robot'),
 'actualTaskNavigation':u['actual-task-navigation']['url'].endswith('/tasks/1098') and 'F181 synthetic navigation F2_TEST_GATE' in u['actual-task-navigation']['text'],
 'refreshFailureRetainsSix':len(u['refresh-failed']['markers'])==6 and '态势刷新失败' in u['refresh-failed']['text'] and '保留上次成功获取的数据' in u['refresh-failed']['text'],
 'retryKeepsLastSuccessTime':updated('refresh-failed')==updated('refresh-retry-retains-data'),
 'automaticRecoveryIdle':len(u['automatic-recovery-completed-idle']['markers'])==6 and '态势刷新失败' not in u['automatic-recovery-completed-idle']['text'] and marker('automatic-recovery-completed-idle','G181 MOBILE_ROBOT')['class'].endswith('marker-online'),
 'mapFailureFallback':len(u['map-failure-list-retained']['markers'])==6 and 'F2.jpg 底图加载失败' in u['map-failure-list-retained']['text'] and 'G145_F013_DISPLAY' in u['map-failure-list-retained']['text'] and any(x['src']=='/F2.jpg' and x['naturalWidth']==0 for x in u['map-failure-list-retained']['images']),
 'eightInvalidOnlyInList':len(u['coordinate-contract-eight-invalid']['markers'])==2 and all(x in u['coordinate-contract-eight-invalid']['text'] for x in ['NULL_X','NULL_Y','BOTH_NULL','NAN','EMPTY','NEGATIVE','OVER_X','OVER_Y']) and '8 个设备缺少有效坐标' in u['coordinate-contract-eight-invalid']['text'],
 'validOriginAndMax':set(x['name'] for x in u['coordinate-contract-eight-invalid']['markers'])=={'CONTRACT_ORIGIN','CONTRACT_MAX'} and 'left: 100%; top: 100%;' in marker('coordinate-contract-eight-invalid','CONTRACT_MAX')['style'],
 'emptySnapshot':not u['empty-contract']['markers'] and '当前没有已登记的设备代理' in u['empty-contract']['text'],
 'activeTaskOfflineImpact':'影响任务 1099（等待异常恢复）' in dialog('offline-active-task-impact') and 'ERR_HEARTBEAT_TIMEOUT' in dialog('offline-active-task-impact'),
 'activeDetailRecovers':'在线/工作状态\t在线·忙碌' in dialog('active-task-recovered-details') and '离线原因码' not in dialog('active-task-recovered-details'),
 'recalibrationNotice':'更换底图尺寸或裁剪范围须重新标定坐标' in u['final-readonly']['text'],
 'noEditorCommandEntry':all(x not in u['final-readonly']['text'] for x in ['下发指令','地图编辑','地图版本管理','轨迹回放']),
 'httpBoundaryAuth':all(api['checks'].values()),
 'currentServiceNullContract':all(service['checks'].values()),
 'allCurrentProtocolCasesPass':all(x.get('result','P')=='P' for x in h['cases']),
 'cleanupAllChecksPass':all(clean['checks'].values()),
 'allProductSourcesUnchangedByGPT':subprocess.check_output(['git','diff','V1.181','--name-only','--','backend','frontend'],cwd=R,text=True).strip()=='',
 'portsReleased':not read('process-cleanup')['listenersAfter']
}
net=h['cases'][-1]['network'];samples=[x for x in net if '/situation/snapshot' in x['path']][:20];gaps=[b['startEpoch']-a['startEpoch'] for a,b in zip(samples,samples[1:])];checks['automaticHttp5s']=len(gaps)==19 and all(4<x<6 for x in gaps);checks['uiNetworkReadOnly']=all(x['path']=='/api/v1/auth/login' for x in net if x['method']!='GET')
failed=[k for k,v in checks.items() if not v];assert failed==['chooserLatestOfflineWithin15s','chooserMembersUpdatedAfterMove'],failed
meta={'tag':'V1.181','productSha':version['productSha'],'handoffSha':version['handoffSha'],'executionBaseline':'V2.4 / BL-008 unchanged','timezone':'Asia/Shanghai','decision':'READY_FOR_CLAUDE (actual receiver Germini)','rules':{'P':7,'F':3,'NT':0},'steps':{'P':4,'F':1,'NT':0},'checks':checks,'assertions':{'P':sum(checks.values()),'F':len(failed)},'issue':'DEF-S3-118','closed':'DEF-S3-048','stillClosed':['DEF-S3-047','NT-S3-024'],'browserSavedCheckpoints':len(uiRows),'checkpointNote':'43原图含1个关闭动画期间未打开候选的前置诊断；保存点不当作独立业务执行次数。','tasks':h['roundTasks'],'refreshSamples':samples,'refreshGapsSeconds':gaps,'networkRequests':len(net),'snapshotRequests':sum('/situation/snapshot' in x['path'] for x in net),'historicalEvidenceReuse':{'businessRules':0,'backendUnitReport':'V1.180 / 1c612d55c9e228b2bdbea1375101648060c9dfc7:464reports,462executedpassed,2skipped','reason':'complete backend tree including pom identical at7a6b7eeec6684ab95cefffc6ffc981b83358ed8e; current fresh frontend build, real JAR health and HTTP/protocol/DB/UI/service contract all observed anew','jarSha256':version['backendArtifactSha256']},'limitations':['controlled model and synthetic protocol adapters; no real hardware or commercial model-quality claim','R07 contract layering, not persisted nullable device E2E; R09 unchanged fixed image, no future map replacement acceptance claim','hover CSS/algorithm checked; no separate real hover interaction P asserted'],'diagnostics':['one Close-animation/marker-click timing: first chooser-before-offline frame contains no dialog; fresh DOM and click produced stable prerequisite before timeout test; original frame preserved','a console inspection attempted to print UTF8 build checkmark through GBK stdout and raised UnicodeEncodeError; original build log remained intact and build was successful; no product failure','no startup/schema/register-limit/SQL-column fixture failures in this round; resources prepared deterministically from V180 experience']}
write('complete-verification',meta)
def update(path,key,changes,snap):
 data=path.read_bytes();dest=E/(P+snap+'-20261108.csv')
 if not dest.exists():dest.write_bytes(data)
 reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')));fields=reader.fieldnames;items=list(reader)
 for r in items:
  if r[key] in changes:r.update(changes[r[key]])
 s=io.StringIO();w=csv.DictWriter(s,fields,lineterminator='\n');w.writeheader();w.writerows(items);path.write_bytes(s.getvalue().encode('utf8'))
index='acceptance/stage3/evidence/'+P+'complete-verification-20261108.json';report='acceptance/stage3/SRS_F023-V1.181-整轮独立复测与统一交修.md'
ruleChanges={}
for i in range(1,11):ruleChanges[f'SRS_F023.R{i:02d}']={'status':'F' if i in [1,3,4] else 'P','verifiedBy':'V1.181当前实测；TC-070.S2候选窗口最新状态/5秒刷新/15秒上限F，网络定时请求P仅子检查；其余全轮见报告','evidence':index+';'+report,'issue':'DEF-S3-118' if i in [1,3,4] else ''}
update(D/'rules.csv','ruleId',ruleChanges,'rules-before')
texts={
 'TC-070.S1':('P','五类默认/逐类/无选择、缩放/全图/平移/滚轮、像素比例和色彩通过；048同坐标及近坐标候选选择、双向切换/混合状态、单设备对照全P。'),
 'TC-070.S2':('F','1098真实任务链接、能力摘要/末报、普通详情更新和协议完成均P，自动HTTP19间隔约5秒P；新增候选窗口在离线21秒后仍在线、移离16秒后仍属重叠，118 F。网络正常不抵销完整视图刷新偏差。'),
 'TC-070.S3':('P','212浏览器请求仅登录POST，其余GET；无指令/编辑/地图版本/轨迹入口。固定1260x6895底图、比例与重标提示当前通过；R09按BL-008部署条件，不宣称未来换图通过。'),
 'TC-071.S1':('P','真实两设备心跳离线/恢复、灰色末位置与红色时间、有关1099/无关任务影响正反通过；真实缺X/Y四请求400/无改、实际控制器null契约及生产浏览器八无效/两有效边界分层通过，不冒写持久空设备E2E。'),
 'TC-071.S2':('P','地图404占位/错误提示/六设备列表保留；刷新503及重试保留六设备和最近成功时间，live恢复自动更新且完成设备空闲；空快照/恢复通过。')}
update(D/'steps.csv','stepId',{k:{'status':v[0],'observedAt':'2026-11-08','actual':'V1.181 / 67fb8960245d08c4d74be85e515bbe325ca21b0f；'+v[1],'evidence':index+';'+report,'issue':'DEF-S3-118' if v[0]=='F' else ''} for k,v in texts.items()},'steps-before')
issueChanges={}
with (D/'issues.csv').open(encoding='utf-8-sig',newline='') as f:
 for row in csv.DictReader(f):
  ident=row['编号']
  if ident in ['DEF-S3-047','DEF-S3-048','NT-S3-024','DEF-S3-118']:
   addition={'DEF-S3-047':'V1.181当前真实离线/恢复、红色时间、原因/时刻、空闲不影响与1099影响任务均通过，保持关闭。','DEF-S3-048':'V1.181当前同坐标/近坐标可靠选择、终端/机器人双向详情切换、离线/忙碌/在线混合层级及单设备正常对照均通过，关闭；新候选刷新缺陷单独118。','NT-S3-024':'V1.181按原BL-008再次执行真实HTTP必填拒绝/无改、控制器5行4断言和八无效/两有效UI契约，分层通过，历史NT保留。','DEF-S3-118':'追加独立分支：候选窗口打开后真实设备从(450,260)移至(100,800)，超过16秒的最新底图/表格已移动，窗口仍称原坐标有两重叠且保留已移离成员。与离线状态陈旧同根；R01/R03/R04完整F，TC070S2 F。'}[ident]
   status={'DEF-S3-047':'V1.181复核保持关闭','DEF-S3-048':'V1.181独立复测关闭（历史V1.180 F保留）','NT-S3-024':'V1.181按BL-008分层复核保持关闭','DEF-S3-118':'V1.181整轮F，状态/位置/候选成员不随刷新更新交Germini'}[ident]
   issueChanges[ident]={'状态':status,'事实':row['事实']+'；2026-11-08追加：'+addition,'证据':row['证据']+';'+index+';'+report}
update(D/'issues.csv','编号',issueChanges,'issues-before')
summary=f'''# SRS_F023 V1.181 整轮独立复测与统一交修

2026-11-08 Asia/Shanghai，V2.4 / BL-008不变。**READY_FOR_CLAUDE（实际接收Germini），整项未通过：规则7P/3F/0NT，五步骤4P/1F/0NT。** 已完成全部可执行适用项，首F后继续全轮；历史业务P复用0。048当前关闭，047/024保持关闭，新增118统一交修。main仍dbd7b5c31ede69aedd25023986a89af9c6bf43ce，无本轮合并/PR、不推进F024，不等于后续需求、三核心场景或95项整体验收通过。

固定产品`67fb8960245d08c4d74be85e515bbe325ca21b0f` / `V1.181`，Germini交接`09b11b9e1e637eb50019fa2f08b820a4da8e24c0`（基于GPT正式交接f4d151ad07bef27fc619886d3606d3c1771fc500）。远端标签/分支实核一致，GPT独立tip-gpt-f013/ai/gpt-test快进接收；未修改产品代码。变更仅三个前端文件，后端完整源码/pom树两版均7a6b7eeec6684ab95cefffc6ffc981b83358ed8e。

| 范围 | 本轮完整裁决 |
| --- | --- |
| R01/R03/R04 | F：新增候选窗口不随最新态势刷新，超过5秒/15秒边界；网络定时请求正常只是P子观察 |
| R02、R05～R10 | 7P；R07/R09仍按BL-008分层防御/固定底图条件执行 |
| TC070S2 | F；任务跳转/普通详情刷新P不抵销候选窗口陈旧 |
| TC070S1/S3、TC071S1/S2 | 4P |
| DEF048 | 当前关闭；同坐标、近坐标、双向切换、优先级和单设备对照通过 |
| DEF118 | 新回归F；状态、位置和候选成员同根陈旧，沿用一个编号 |

## 118反例与合法对照

1. 两真实HTTP/持久设备G145_F013_DISPLAY（G181 SMART_DISPLAY）/G180_F023_0（G181 MOBILE_ROBOT）同在(450,260)、ONLINE/IDLE。打开“选择重叠设备”后停止显示终端的真实协议心跳；实际超时事件offlineAt=07:09:36.170465。UI最近成功快照07:09:57.361381已超过21秒，底图灰色/表格离线及ERR_HEARTBEAT_TIMEOUT均已更新，候选窗口仍显示终端“在线·空闲”。原始快照/SQL、截图和全部窗口文本保留。
2. 恢复/正常任务后再打开候选窗口，将终端经真实协议状态上报移至(100,800)，与机器人(450,260)不再重叠。等待16秒以上，表格和底图都显示新坐标，候选窗口仍称(450,260)有两个重叠设备、保留已移离的G145成员。不是整个服务/网络刷新失败，不靠源码推断F。
3. 合法对照：关窗重开、普通详情选中/五秒刷新及直接/peer切换都能显示当前状态；原048点击遮挡问题已通过新增候选交互关闭。118只针对新增选择器缓存对象未更新，不重复登记048。首次F检查点`dae811052be963c8795d0ba4193740d373540fd6`已推送后继续完整范围。

修复要求：候选选择器按最新设备快照同步状态、坐标、能力与候选成员，维持目标设备身份；设备移离/不再启用/消失时不能留下虚假重叠候选。保留048现有可靠选择与切换、层级、几何、原坐标和任务链接，不能把候选面板改成无限期静态快照或放宽刷新标准。

## 已完成覆盖与证据层级

原048同/近坐标正确选择DISPLAY、机器人/终端双向切换；不同离线/忙碌/在线层级和非重叠单设备直接点击均当前P。默认五类全选/逐类/无选、125%/100%/全图、拖动/滚轮、三种缩放下像素锚点/比例、自然图片1260x6895、重标提示和只读范围全部当前执行。不能把本轮未独立执行的悬停动作写成UI P，CSS/算法自检层级另列。

两真实HTTP任务1098正常承接、实际业务指令、成功反馈/事件/持久COMPLETED与真实浏览器链接；1099执行中真实心跳离线显示“影响任务1099”、灰色末位置/红色最后上报/原因/时刻及恢复，最后人工终止释放。空闲终端离线“不影响任务”正反当前通过。未SQL伪造业务生命周期，模型受控、设备为协议合成，不扩大到商业模型质量或物理硬件。

当前HTTP缺X/Y四次400/配置不变、三角色snapshot200/匿名401；实际控制器5行/4断言保留null X/null Y/双null；生产浏览器8类无效（null X/Y/双null/空串/NaN/负数/X越界/Y越界）仅列表、原点与最大边界正确。按BL-008分层，不宣称可持久空坐标设备E2E。固定底图未更换，R09检查现有资源/几何/提示与只读，未来变尺寸/裁剪仍必须实施方全设备重标再验收。

地图404占位/失败提示及六设备列表；快照503和重试保留六设备及最近成功更新时间、失败时间可见；live恢复后自动刷新并显示已完成任务设备空闲；空态/恢复通过。浏览器{len(net)}真实代理请求，除登录POST外全GET，snapshot{meta['snapshotRequests']}次；首20自动样本19间隔{min(gaps):.3f}～{max(gaps):.3f}秒。**这一网络P不抵销候选窗口实际不刷新的R03/R04 F。**

前端独立生产build成功（38.99秒，保留既有大chunk提示），现有marker算法自检通过；当前真实JAR健康UP、HTTP/SQL/协议、独立服务契约均实际执行。后端未变，复用V1.180全量464报告/462执行通过/2原跳过及同源码生产JAR，完整源码树/当前JAR SHA256见version-alignment；未冒写为V1.181重新执行464单测或重新构建后端。所有F023业务规则观察均当前，历史业务P替代0。

本轮43浏览器保存点含1关闭动画期间未打开候选的前置诊断帧，fresh DOM后重新建立有效前置才执行超时；不把重复/稳定后保存点计为新增业务次数。总核对{len(checks)}断言（{sum(checks.values())}P/2F），2F同属118，与规则/步骤数量分开。GBK stdout打印构建日志checkmark失败为采证显示诊断，UTF8原日志/成功结果完整，不记产品F。

## 清理与交接

自有schema tip_gpt_f006_v118_20261030 / Redis10，18129后端/18117模型/15179前端代理/18132～18134协议/18135控制。三设备INACTIVE、定义DISABLED、名称/坐标/接口/配置原值和能力启停原值恢复，RESOURCE_CRITICAL内容/启用恢复，真实版本/审计递增保留。2任务终态，本轮活跃分配0、全库代理占用0、注入触发器0；原26历史分配状态行ID/任务/状态逐项前后完全相同。失败/版本/证据保留，不清历史任务。两自有进程确认命令后停止，七端口释放，产品源码对V1.181无变化，未写主工作区用户文件、共享PG/Redis或Germini资源。

总索引`{index}`；当前HTTP/SQL/protocol、chooser-stale-counterexample、43原图/UI JSON、API-auth、service-contract、生产构建/marker检查、cleanup-final/process-cleanup、原台账快照及SHA256清单同目录。可重跑夹具`probe-f023-v181-runtime.py`与独立服务`F023SnapshotContractProbeV181.java`。先提交并推完整证据，再GPT单写正式HANDOFF/ROADMAP，记录实际证据SHA；之后按用户授权在原Germini F023修复对话交118，修复期每10分钟核查，再新唯一版本按V2.4重新全轮。F027/F028既有预修复对话继续保留，尚不推进。
'''
(D/Path(report).name).write_bytes(summary.encode('utf8'))
progress=D/'阶段3-复测进度.md';t=progress.read_text(encoding='utf8');intro='\n\n- **2026-11-08 / F023 V1.181 / V2.4：READY_FOR_CLAUDE（Germini），7P/3F/0NT、五步骤4P/1F/0NT**。048当前关闭，047/024保持；新118候选窗口状态及位置/成员不随最新快照更新，超过15秒仍旧值，R01/R03/R04及TC070S2 F。原始故障后继续43 UI保存点/2真实任务/当前API、SQL、服务契约及生产前端构建全部范围；后端树相同历史464组件报告复用明确分层，不冒认当前重跑。资源恢复/当前分配占用0、原26历史状态行不变、2进程/七端口清理。报告`SRS_F023-V1.181-整轮独立复测与统一交修.md`。证据先推后正式交接，main仍dbd7b5c，无合并/PR，不推进F024。\n';progress.write_bytes((t.split('\n',1)[0]+intro+t.split('\n',1)[1]).encode('utf8'))
print('Registered',len(checks),'assertions',sum(checks.values()),'P',len(failed),'F; rules7P3F; steps4P1F')
