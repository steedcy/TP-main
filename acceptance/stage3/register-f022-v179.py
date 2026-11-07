"""Record full current-version acceptance only after every observation and cleanup pass."""
from pathlib import Path
import csv,json
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3';E=D/'evidence';PRE='SRS_F022-V1.179-'
SHA='7e86a0afb7169154a9ec7b2b12c7eda60e4851af';HANDOFF='e349145b658f221029d9aaa971c39f78f5bbc24a';MAIN='413e1b3aee20116bb612ed1d4dac96e9937cde0e'
def get(name):return json.loads((E/(PRE+name+'-20261107.json')).read_text(encoding='utf-8-sig'))
def put(name,x):
    p=E/(PRE+name+'-20261107.json');assert not p.exists();p.write_bytes(json.dumps(x,ensure_ascii=False,indent=2).encode('utf-8'))
primary=get('http');base=json.loads((E/(PRE+'http-20261107-baseline.json')).read_text(encoding='utf-8'));tail=json.loads((E/(PRE+'http-20261107-replan-baseline.json')).read_text(encoding='utf-8'));mixed=json.loads((E/(PRE+'http-20261107-mixed-clauses.json')).read_text(encoding='utf-8'));flight=json.loads((E/(PRE+'http-20261107-flight-preset.json')).read_text(encoding='utf-8'))
ui=get('ui');state=get('fixture-cleanup');quality=get('final-quality-review');tests=get('backend-tests');container=get('container-component');process=get('process-cleanup')
raw=[primary,base,tail,mixed,flight]
assert all(x.get('endedAt') and not x['diagnostics'] and all(c.get('result')=='P' for c in x['cases']) for x in raw)
assert tests['totals']=={'tests':463,'failures':0,'errors':0,'skipped':2}
assert container['container']=={'started':True,'mapperInjected':True,'taskMapperInjected':True} and all(c['result']=='P' for c in container['componentObservations'])
assert len(ui['groups'])==19 and all(x['result']=='P' for x in ui['groups']) and ui['consoleErrorCount']==0
assert state['allTasksTerminal'] and state['currentActiveAssignments']=='0' and state['presetBusinessAndRawJsonRestored'] and process['allReleased']
assert quality['mainUserFileHashesUnchanged'] and not quality['productSourceDiff']
assert len(state['taskIds'])==37 and len(state['definitionIds'])==7 and len(state['templateIds'])==2
effective=[dict(c,source=PRE+'http-20261107.json') for c in primary['cases']]
for x,label in [(mixed,'mixed-clauses'),(base,'baseline'),(tail,'replan-baseline')]:effective += [dict(c,source=PRE+'http-20261107-'+label+'.json') for c in x['cases'] if 'trial' not in c['name']]
assert len(effective)==40 and all(c['result']=='P' for c in effective)
find=lambda x,n:next(c for c in x['cases'] if c['name']==n)
idof=lambda x,n:find(x,n)['taskId']
gap=find(primary,'unknown-and-no-enabled-capability');assert all(r['response']['body']['code']==4604 for r in gap['requests'])
six=[find(primary,n) for n in ['116-whitelist-shorter-valid-area','116-capability-sentence-legal']]+[find(base,'baseline-location-prohibited'),find(tail,'replan-baseline-prohibited-tail')]+[find(mixed,n) for n in ['mixed-prohibit-location-allow-cap-comma','mixed-allow-cap-prohibit-location-comma']]
put('DEF-S3-116-closure',{'tag':'V1.179','productSha':SHA,'status':'CLOSED current independent full round','historicalFailuresRetained':['V1.175 task997','V1.177 tasks1011/1012/1021/1024','V1.178 tasks1049/1050'],'sixSpecificRetests':six,'mixedPositiveNegativeConnectorControls':mixed['cases'],'initialAndReplanBaselineControls':{'initial':[c for c in base['cases'] if 'trial' not in c['name']],'replan':[c for c in tail['cases'] if 'trial' not in c['name']]},'scope':'Current R07 includes original prohibition/whitelist/capability/complete-condition, autonomous/replan/baseline parameter mappings, comma/order/connector semantics. All applicable assertions current P; no historical P substituted.'})
put('probe-corrections',{'launchOnlyDiagnostic':{'source':PRE+'replan-baseline-launch-diagnostic-20261107.txt','reason':'Tail probe omitted from this round initial copy list. Sequential runner stopped at missing-file exit before any tail HTTP task. Added unchanged-version adapted independent script and ran required tail legal/prohibited branches successfully.','actualReplanBaselineTrialsAndTasks':[c.get('taskId') for c in tail['cases']],'noBusinessObservationOverwritten':True,'noProductChange':True},'uiNavigation':ui['navigationNote'],'sequencing':'Flight fully cleaned before primary; API boundary snapshots complete before UI config writes; UI finish releases sequential mixed/baseline chain; corrected last tail run starts after earlier adapters exited. All current observations retained, no duplicate successful observation manufactured.','businessDiagnostics':[]})
notes={
'R01':'三预置删除/身份保护、参数及约束维护、业务字段及原JSON恢复；自有航班适配器实际能力测试通过。',
'R02':f'同定义{idof(primary,"same-definition-two-step")}两步与{idof(primary,"same-definition-five-step")}五步自主完成，定义未写死步骤。',
'R03':'创建/编辑约束省略/null/空白/501拒绝，1/500中文持久；名称1/64、目标1/500、重名409/必填；真实UI默认空、参数编辑、边界/回显及四类型提交通过。',
'R04':'扩展沿既有页面、统一合成设备协议及现有CAP_NAVIGATION运行，无新增产品页面/协议/能力类型。',
'R05':'当前五动作及条件+五动作完成、六动作拒绝；真实重规划前缀1+4合并五步、1+5超额度拒绝，每版/实际路径≤5。',
'R06':'未知/无启用有效能力的创建与更新均400/4604，定义表无变化、能力状态恢复，合法NAV对照通过。',
'R07':'116六个历轮反例、原禁止/白名单/能力及完成条件、首次/局部重规划自主与基线映射均P；逗号/顺序/分号/并且/同时合法及禁区反控共八组全部通过。',
'R08':'创建/修改/启用/停用审计完整，停用不影响已运行计划完成；真实UI任务1080参数精确持久、停用不可新选且详情仍可读。'}
stepNotes={'TC-068.S1':'新增编辑边界/三预置/默认空/参数编辑/真实保存回显通过。','TC-068.S2':'动态四类型真实提交、约束/完成条件、五步及重规划预算、停用/已有任务/审计全部当前通过。','TC-069.S1':'三预置标识清楚/不可删除/身份保护，参数约束可编辑并恢复通过。','TC-069.S2':'重名/缺必填/空白/501/未知或未启用能力拒绝，定义无污染且非法项不可选。'}
report='SRS_F022-V1.179-整轮独立复测与验收.md';ref='acceptance/stage3/'+report+';acceptance/stage3/evidence/'+PRE+'complete-verification-20261107.json'
for name in ['steps.csv','rules.csv','issues.csv']:
    p=D/name
    with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);heads=reader.fieldnames;rows=list(reader)
    for x in rows:
        if name=='steps.csv' and x['stepId'] in stepNotes:x.update(status='P',observedAt='2026-11-07',actual='V1.179当前整轮实测P：'+stepNotes[x['stepId']]+'；原F/NT保留在ledger-before及历史报告。',evidence=x['evidence']+';'+ref,issue='')
        elif name=='rules.csv' and x['requirement']=='SRS_F022':x.update(status='P',verifiedBy='V1.179全部适用项当前实测；'+notes[x['ruleId'].split('.')[-1]],evidence=x['evidence']+';'+ref,issue='')
        elif name=='issues.csv' and x['编号'] in ['DEF-S3-028','DEF-S3-029','DEF-S3-030','DEF-S3-117']:
            x['状态']='关闭（V1.179当前独立实测保持，旧失败保留）';x['事实']+='；V1.179创建编辑边界/API/真实动态四类型UI与任务提交持久、实际JAR健康UP及Spring双mapper注入当前通过。';x['证据']+=';'+ref
        elif name=='issues.csv' and x['编号']=='DEF-S3-116':
            x['状态']='关闭（V1.179整轮当前独立实测通过）';x['事实']+='；V1.179六个历轮反例全部当前通过，八组混合子句正反对照含连接词通过；首次/重规划基线实际映射目标禁区拒绝、不冻结/不下发，合法对照完成。原V1.175/V1.177/V1.178失败及探针诊断保留。';x['证据']+=';'+ref+';acceptance/stage3/evidence/'+PRE+'DEF-S3-116-closure-20261107.json';x['阶段4动作']='已完成当前F022整轮闭环；保持原反例/合法/禁区/重规划基线/混合子句回归，后续需求按顺序交接，不扩大95项整体验收。'
    with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=heads,lineterminator='\n');w.writeheader();w.writerows(rows)
index={'verdict':'REQUIREMENT_PASSED','tag':'V1.179','productSha':SHA,'claudeHandoffSha':HANDOFF,'executionBaseline':'V2.4','timezone':'Asia/Shanghai','rules':{'P':8,'F':0,'NT':0},'steps':{'P':4,'F':0,'NT':0},'notes':notes,'stepNotes':stepNotes,'closed':['028','029','030','116','117'],'openCurrentRequirement':[],'historicalPReused':0,'businessGroups':{'total':40,'P':40,'F':0,'NT':0,'counting':'28 primary +8 mixed clauses +2 baseline +2 replan-baseline. Two successful trial prerequisites and supplementary same-preset flight observation not extra business groups. UI/SQL/protocol of same task not recounted.'},'tasks':{'total':37,'ids':state['taskIds'],'allHttpCreated':True,'businessTasks':35,'trialPrerequisites':[idof(base,'baseline-publication-trial'),idof(tail,'replan-baseline-two-step-trial')],'sqlSynthesizedLifecycle':0},'ui':{'groups':19,'P':19,'F':0,'screenshots':19,'consoleErrors':0,'navigationScope':ui['navigationNote']},'backendTests':tests['totals'],'container':container['container'],'layers':['unit/service','actual production JAR','authenticated real HTTP','SQL/events/audit/plan versions/commands','controlled model','synthetic device protocol/callbacks','actual IAB UI'],'physicalDevices':False,'affectedAdjacency':'F013 family-constraint subrange currently passed from same observations; F019 real replan/baseline/remaining-budget currently passed. Original historical acceptance versions retained.','environment':{'retainedDefinitions':7,'templates':2,'ownedDevices':4,'terminalTasks':37,'activeAssignments':0,'occupiedAgents':0,'portsReleased':7,'mainUserfilesUnchanged':40},'mainAtTestCompletion':MAIN,'mainIntegration':'authorized next step only after complete evidence and formal handoff pushed; actual remote integration recorded separately','next':'Safely merge accepted test branch to main and verify remote; then only F023 sequential Claude handoff, no later/core/95 overall acceptance claim'}
put('complete-verification',index)
text=f'''# SRS_F022 V1.179 整轮独立复测与验收

**REQUIREMENT_PASSED：八规则8P/0F/0NT，正式四步骤4P/0F/0NT。** 全部适用项本轮实测，历史P复用0；028/029/030/117保持关闭，116本轮关闭。原失败、探针诊断及历轮报告均保留。

固定产品`{SHA}` / **V1.179**，Claude交接`{HANDOFF}`，远端实际分支/标签一致。GPT独立 `C:/Users/savy/Desktop/TIP-main/tip-gpt-f013` / ai/gpt-test；2026-11-07 Asia/Shanghai，执行基线V2.4，无业务标准变更。main在测试结束时仍`{MAIN}`；先推完整证据及正式交接，再按授权安全同步main，实际远端结果另附，不提前声明已合入。产品源码对标签diff为空。ROADMAP暂存030已实际纳入02a38cb，当前边界/UI通过；既有041依赖未变，不凭“待移植/已修复”字样裁决。

| 规则 | 当前 | 实测证据 |
| --- | --- | --- |
'''
for k,v in notes.items():text+=f'| SRS_F022.{k} | P | {v} |\n'
text+='\n| 正式步骤 | 当前 | 当前范围 |\n| --- | --- | --- |\n'
for k,v in stepNotes.items():text+=f'| {k} | P | {v} |\n'
text+='''
116闭环反例与合法对照：1071只允许GATE但候选F2_TEST被拒绝/未冻结/无执行；1072“仅允许使用CAP_NAVIGATION能力”合法导航完成；1090首次基线合法完成/1091模型503降级到实际试运行成功启用模板后禁区映射拒绝；1093真实前缀完成→实际失败重试/候选切换→局部重规划高风险转基线合法尾部完成，1094禁区fallbackLocation尾部拒绝，前缀保留、基线不冻结、无禁区指令。原禁止反例1068及自主重规划1079禁区拒绝，合法1067/1069及其他区域1070对照通过。

1081～1088混合子句八组：同义分号、两个原逗号反例（1082/1083）及反序表达、允许地点/禁止其他能力、两种逗号禁区反向对照、并且/同时连接词合法控制均当前P。原逗号反例现为三类PASS并实际完成；禁区目标仍硬拒绝/未冻结/无执行，不以普遍放行制造P。定义原文确实持久且初始模型请求包含同文，任务候选、数据库计划、事件与仿真设备指令共证。按原自然语言业务含义裁决，未要求用户仅用分号。六反例及所有正反对照详见`evidence/SRS_F022-V1.179-DEF-S3-116-closure-20261107.json`和各http原始文件。

40去重业务观察全P：28主批次、8混合子句、2首次基线、2重规划基线；37任务1058～1094均HTTP创建（35业务、1089/1092两次成功试运行前置），无SQL合成生命周期。19组真实IAB/19截图全P、0当前UI console error。配置创建/编辑、动态字段/非法类型、实际提交、停用选项均真实操作；已有任务详情通过已知HTTP创建ID直达读取并核对计划/事件。自动点击窄列换行详情锚点未导航，不把该动作声称为成功，保留navigationNote；直达真实页面满足既有任务可读取断言，未用API/源码替代页面展示。

必要邻接F013任务族约束硬门、F019真实重规划/基线/剩余预算及核心认证/任务入口当前实测通过，同一观察共证不增加次数，历史验收行保留原版本。单轮`mvn -o test`463报告、461执行通过、2原有跳过、0失败/错误；`mvn -o package -DskipTests`与`npm run build`成功。实际打包JAR健康UP且完整HTTP/业务入口运行；独立打包类Spring容器构造成功，TaskDefinitionMapper、TaskMapper实际注入，四服务对照P。模型为受控HTTP、设备为合成适配器，不代表商业模型质量或物理硬件验收。

执行与诊断：本轮API快照全部完成后才做UI配置写入，无前轮快照/新建交叠误报。能力状态恢复批量事务减少逐行客户端启动，断言不变。末尾重规划探针遗漏于最初复制清单，顺序启动器在缺文件处立即拦截，未产生业务任务；补齐同版独立脚本后完成真实试运行与正反分支，原启动日志保留在replan-baseline-launch-diagnostic，不记产品F或重复业务实测。所有业务原始组无诊断/遗漏裁决，无剩余NT，未改产品修复来替代测试。

资源：GPT schema tip_gpt_f006_v118_20261030、Redis10，18129后端/18117模型/15179前端/18132～18135适配器，与Claude隔离。37任务终态，失败历史及计划/事件/指令保留；7定义DISABLED、2模板DISABLED、4设备INACTIVE，当前活跃分配/占用/触发器0，三预置业务字段和原JSON恢复、临时能力状态恢复、实际能力测试记录保留。3自有进程树停止、七端口无监听，主工作区40用户文件开工/结束哈希不变，无强推/reset。未改共享服务/Claude资源/风险规则，原Office、凭据/令牌、JAR、DPAPI与无关用户文件不提交，公开日志临时口令脱敏。

本报告是F022当前范围验收通过，不代表F023及后续、三核心场景或95项整体验收通过。完整证据先提交推送，再同步HANDOFF/ROADMAP/EXECUTION_BASELINE与无业务基线变更记录；main实际合入及远端核验另记独立证据，唯一产品标签不移动。下一需求仅F023顺序交Claude，不能把原后续台账的历史P/F/NT当本轮验收。
'''
(D/report).write_bytes(text.encode('utf-8'))
p=D/'阶段3-复测进度.md';s=p.read_text(encoding='utf-8');s+='\n\n2026-11-07 F022 V1.179整轮REQUIREMENT_PASSED：8规则/4步骤全部当前P，历史P复用0；40业务组/37 HTTP任务/19 IAB组全P，463报告461通过2原有跳过；116六原反例及八混合正反组关闭、028/029/030/117保持。7定义2模板4设备停用、分配/占用0、三树七端口清理、40用户文件哈希不变。证据先推送后按授权安全合main并另记实证，下一仅F023；原F/诊断保留。详见'+report+'。\n';p.write_bytes(s.encode('utf-8'))
print('Registered F022 V179 REQUIREMENT_PASSED:8 rules/4 steps all P,40 groups37 tasks19 UI, current only.')
