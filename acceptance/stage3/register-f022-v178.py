"""Register the completed V178 full round without rewriting historical evidence."""
from pathlib import Path
import csv,json,hashlib
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3';E=D/'evidence';PRE='SRS_F022-V1.178-'
SHA='18aeeabd6991bb5150c214a3abb3cc7ee142b97f';HANDOFF='49d112f8fb4ee5515ba8811a10150447e9a3bfa8';MAIN='413e1b3aee20116bb612ed1d4dac96e9937cde0e'
def get(suffix):return json.loads((E/(PRE+suffix+'-20261107.json')).read_text(encoding='utf-8-sig'))
def put(name,x):
    p=E/(PRE+name+'-20261107.json');assert not p.exists();p.write_bytes(json.dumps(x,ensure_ascii=False,indent=2).encode('utf-8'))
main=get('http');base=json.loads((E/(PRE+'http-20261107-baseline.json')).read_text(encoding='utf-8'));tail=json.loads((E/(PRE+'http-20261107-replan-baseline.json')).read_text(encoding='utf-8'));mixed=json.loads((E/(PRE+'http-20261107-mixed-clauses.json')).read_text(encoding='utf-8'));gap=json.loads((E/(PRE+'http-20261107-capability-gap-stable.json')).read_text(encoding='utf-8'));flight=json.loads((E/(PRE+'http-20261107-flight-preset.json')).read_text(encoding='utf-8'))
state=get('fixture-cleanup');quality=get('final-quality-review');tests=get('backend-tests');ui=get('ui');container=get('container-component')
assert get('process-cleanup')['allReleased']
assert state['presetBusinessAndRawJsonRestored'] and state['allTasksTerminal'] and state['currentActiveAssignments']=='0'
assert quality['mainUserFileHashesUnchanged'] and quality['productSourceDiff']==''
assert tests['totals']=={'tests':460,'failures':0,'errors':0,'skipped':2}
assert container['container']=={'started':True,'mapperInjected':True,'taskMapperInjected':True} and all(x['result']=='P' for x in container['componentObservations'])
assert ui['effectiveGroups']==19 and ui['consoleErrorCount']==0
assert all(x['result']=='P' for x in ui['groups'] if not x.get('correction'))
assert all(x.get('endedAt') and not x['diagnostics'] for x in [main,base,tail,mixed,gap,flight])
find=lambda x,n:next(c for c in x['cases'] if c['name']==n)
failedProbe=find(main,'unknown-and-no-enabled-capability');stable=find(gap,'unknown-and-no-enabled-capability')
assert failedProbe['checks']=={'allFour400':True,'capabilityGapExplained':True,'invalidNoDefinitionMutation':False,'fixtureRestored':True}
assert stable['result']=='P'
effective=[dict(c,source=PRE+'http-20261107.json') for c in main['cases'] if c['name']!='unknown-and-no-enabled-capability']+[dict(stable,source=PRE+'http-20261107-capability-gap-stable.json')]
for x,label in [(base,'baseline'),(tail,'replan-baseline'),(mixed,'mixed-clauses')]:
    effective += [dict(c,source=PRE+'http-20261107-'+label+'.json') for c in x['cases'] if 'trial' not in c['name']]
assert len(effective)==36 and sum(c['result']=='F' for c in effective)==2
assert len(state['taskIds'])==33
failures=[c for c in effective if c['result']=='F'];assert {c['taskId'] for c in failures}=={1049,1050}
originalControls=[find(main,n) for n in ['116-whitelist-shorter-valid-area','116-capability-sentence-legal']]+[find(base,'baseline-location-prohibited'),find(tail,'replan-baseline-prohibited-tail')]
assert all(c['result']=='P' for c in originalControls)
put('DEF-S3-116-final-counterexamples',{'tag':'V1.178','productSha':SHA,'issue':'DEF-S3-116 residual mixed capability/location clause false rejection; original V177 four exact cases now P, issue not closed','expected':'Two explicit constraints apply independently: prohibit GATE location, allow NAV capability. NAV to ZONE_A satisfies both. Ordinary Chinese comma and clause order do not reverse their meaning.','failures':failures,'controls':[c for c in mixed['cases'] if c['result']=='P'],'originalFourRetest':[{'name':c['name'],'taskId':c['taskId'],'checks':c['checks'],'result':c['result']} for c in originalControls],'noDuplicateIssue':True,'reproduce':'Run current start support/JAR fixtures then mixed-clauses probe sequentially, own schema/Redis10 only; see source and raw request/model/plan/events/commands in cases.','goalControl':'The semicolon/comma pair uses the same typed scene and candidate NAV to ZONE_A; model goal fixture and wrapper target suffix are unchanged across controls. Failure explicitly names prohibited NAV, not goal mismatch. Actual definition text and model request both captured.'})
put('probe-corrections',{'definitionMutationProbe':{'source':PRE+'http-20261107.json','case':'unknown-and-no-enabled-capability','observedFalseAssertion':'Whole definition table changed while independent UI created definition107 G178 UI acceptance; all four invalid requests returned400 and capability states restored.','newAuthorizedRow':107,'replacement':PRE+'http-20261107-capability-gap-stable.json','stableResult':'P, without browser configuration writes; existing current fixture reused, no new historical P','rawFailureRetained':True},'uiTransitionProbe':{'source':PRE+'ui-20261107.json','rawName':'disabled-options','reason':'Route/dialog transition left dialog closed; premature option visibility assertion failed. Fresh AX, explicit dialog reopen and disabled-options-confirmed passed.','effectiveGroups':19,'rawCaptures':20,'rawObservationRetained':True},'sequencing':'Flight cleanup ended before business tasks; primary config/API boundary check overlapped only authorized UI definition creation, corrected independently. After primary UI sentinel, capability-gap/mixed/baseline/replan-baseline run in one sequential process chain. No competing adapter instances.','productFailures':'1049 and1050 remain product F, not reclassified as probe errors.'})
notes={
'R01':'三预置删除400、身份保护、参数/约束编辑及原JSON恢复全部当前通过；航班有效能力由自有适配器实际测试。',
'R02':'同定义1025两步、1026五步自主完成，定义未预写步骤。',
'R03':'创建/编辑省略/null/空白/501拒绝，1/500中文合法持久；名称1/64、目标1/500、重名409/必填；四类型API/真实UI提交1047。028/029/030当前保持关闭。',
'R04':'沿既有定义/提交/详情页面、统一合成设备协议和现有CAP_NAVIGATION运行，无新增产品页面、协议或能力类型。',
'R05':'1026五步、1033条件+五动作完成；1027六步拒绝；1044前缀1+4合并五步、1045超额度拒绝；当前路径及版本均≤5。',
'R06':'未知/未启用有效能力POST/PUT均400且状态恢复；暂停UI配置写入的补测确认非法请求不改变定义表，原探针误报保留。',
'R07':'V177四处具体反例1038/1039/1054/1057本轮均P，原禁区1035、自主重规划1046拒绝及合法对照P；但混合逗号约束1049/1050错误禁止NAV，R07仍F。完成条件、能力范围子项P不抵销整项F。',
'R08':'创建/修改/启用/停用审计完整；1031停用后已有任务完成，1047真实提交后停用不可新选、已有任务可读。'}
stepNotes={'TC-068.S1':'创建编辑边界、三预置、默认空及参数编辑、真实保存回显通过。','TC-068.S2':'动态四类型/真实提交持久、五步/完成条件、停用/已有任务/审计P；混合约束1049/1050 F。','TC-069.S1':'三预置不可删除、身份保护及参数约束可编辑恢复、UI标识和禁删通过。','TC-069.S2':'重名409、缺必填/空白/501、未知/未启用能力拒绝，无非法定义进入选项；探针隔离补测P。'}
report='SRS_F022-V1.178-整轮独立复测与统一交修.md';ref='acceptance/stage3/'+report+';acceptance/stage3/evidence/'+PRE+'complete-verification-20261107.json'
for name in ['steps.csv','rules.csv','issues.csv']:
    p=D/name
    with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);heads=reader.fieldnames;rows=list(reader)
    for x in rows:
        if name=='steps.csv' and x['stepId'] in stepNotes:x.update(status='F' if x['stepId']=='TC-068.S2' else 'P',observedAt='2026-11-07',actual='V1.178当前整轮实测：'+stepNotes[x['stepId']]+'；历史原文及原F/NT保留在ledger-before和历史报告。',evidence=x['evidence']+';'+ref,issue='DEF-S3-116' if x['stepId']=='TC-068.S2' else '')
        elif name=='rules.csv' and x['requirement']=='SRS_F022':x.update(status='F' if x['ruleId']=='SRS_F022.R07' else 'P',verifiedBy='V1.178当前全部适用项实测；'+notes[x['ruleId'].split('.')[-1]],evidence=x['evidence']+';'+ref,issue='DEF-S3-116' if x['ruleId']=='SRS_F022.R07' else '')
        elif name=='issues.csv' and x['编号'] in ['DEF-S3-028','DEF-S3-029','DEF-S3-030','DEF-S3-117']:
            x['状态']='关闭（V1.178当前独立实测保持，历史失败保留）';x['事实']+='；V1.178动态四类型/真实UI/创建编辑边界，实际JAR UP与Spring双mapper注入通过。';x['证据']+=';'+ref
        elif name=='issues.csv' and x['编号']=='DEF-S3-116':
            x['状态']='待修复（V1.178原四反例P，混合约束两处误拒绝F）';x['事实']+='；V1.178原1038短地点拒绝、1039合法能力完成、1054首次基线拒绝、1057重规划基线尾部拒绝均P；1049禁止GATE逗号仅允许NAV、1050逆序逗号表达均把合法NAV到ZONE_A错误拒绝，1048同义分号及1051另一合法逗号表达完成。';x['证据']+=';'+ref+';acceptance/stage3/evidence/'+PRE+'DEF-S3-116-final-counterexamples-20261107.json';x['阶段4动作']='修正混合能力/地点自然语言子句的极性和作用域，普通中文逗号/顺序不得将地点禁止套到合法能力；保持V178原四反例与基线映射、Spring注入关闭行为，新唯一标签后F022再整轮。'
    with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=heads,lineterminator='\n');w.writeheader();w.writerows(rows)
index={'verdict':'READY_FOR_CLAUDE','tag':'V1.178','productSha':SHA,'claudeHandoffSha':HANDOFF,'executionBaseline':'V2.4','timezone':'Asia/Shanghai','rules':{'P':7,'F':1,'NT':0},'steps':{'P':3,'F':1,'NT':0},'notes':notes,'stepNotes':stepNotes,'closed':['028','029','030','117'],'open':['116'],'originalFourSpecificCounterexamples':'all current P; does not close entire116','historicalPReused':0,'businessGroups':{'total':36,'P':34,'F':2,'counting':'28 primary groups with isolated no-mutation correction replacing its invalid observation; two baseline + two replan baseline + four mixed clauses. Trial prerequisites2, flight supplementary same-preset observation, same-task UI/SQL/protocol do not add business groups.'},'tasks':{'total':33,'ids':state['taskIds'],'allHttpCreated':True,'businessTasks':31,'successfulTrialPrerequisites':[1052,1055],'sqlSynthesizedLifecycle':0},'ui':{'effectiveGroups':19,'P':19,'F':0,'rawCaptures':20,'probeCorrections':1,'consoleErrors':0,'note':'Product error display is UI P, business remainsF.'},'backendTests':tests['totals'],'container':container['container'],'layers':['unit/service','actual production JAR','authenticated HTTP','SQL/events/audit/versions/commands','controlled model','synthetic device callbacks','actual IAB UI'],'physicalDevices':False,'directAffectedAdjacency':'F013.R03 family-constraint subrange currentF from same mixed-clause observations; F019 replan/baseline/step budget current tested. Historical accepted rows retained at original versions.','environment':{'definitions':len(state['definitionIds']),'templates':len(state['templateIds']),'ownedDevices':4,'allTasksTerminal':True,'activeAssignments':0,'occupiedAgents':0,'portsReleased':7,'mainUserFilesUnchanged':40},'main':MAIN,'noMergeNoPR':True,'next':'Claude repair residual116 mixed-clause semantics, keep old four/117/028029030, new tag and F022 full round; no F023/core/95 acceptance claim'}
put('complete-verification',index)
text=f'''# SRS_F022 V1.178 整轮独立复测与统一交修

**READY_FOR_CLAUDE：规则7P/1F/0NT，正式四步骤3P/1F/0NT。** 全部适用项本轮实测、历史P复用0。V1.177四处具体反例当前均通过；DEF-S3-116仍因混合自然语言约束误拒绝F，整项未通过、不合main。028/029/030/117当前保持关闭。

产品`{SHA}` / **V1.178**，Claude完整交接`{HANDOFF}`；远端实际标签/分支核对一致，GPT快进接收。V2.4，2026-11-07 Asia/Shanghai，独立worktree `C:/Users/savy/Desktop/TIP-main/tip-gpt-f013` / ai/gpt-test。main仍`{MAIN}`，F001～F021已验收，当前产品源码对标签diff为空。ROADMAP暂存030已实际纳入02a38cb并当前边界/UI通过，不能以旧表代替本轮验收。

| 规则 | 当前 | 当前证据 |
| --- | --- | --- |
'''
for k,v in notes.items():text+=f'| SRS_F022.{k} | {"F" if k=="R07" else "P"} | {v} |\n'
text+='\n| 正式步骤 | 当前 | 当前范围 |\n| --- | --- | --- |\n'
for k,v in stepNotes.items():text+=f'| {k} | {"F" if k=="TC-068.S2" else "P"} | {v} |\n'
text+='''
DEF-S3-116残留（不重复编号）：

| 任务 | 定义约束/实际候选 | 预期/实际 |
| --- | --- | --- |
| 1048 合法对照 | “禁止前往F2_TEST_GATE；仅允许使用CAP_NAVIGATION能力。”；NAV到F2_ZONE_A | 满足两项约束；三类PASS、冻结并实际完成，P |
| 1049 反例 | “禁止前往F2_TEST_GATE，仅允许使用CAP_NAVIGATION能力。”；同一NAV到F2_ZONE_A | 仅将分号换逗号，仍应合法；却constraint FAIL，错误列NAV为禁止能力，转人工；无冻结/执行，F |
| 1050 顺序分支 | “仅允许使用CAP_NAVIGATION能力，禁止前往F2_TEST_GATE。”；同一NAV到F2_ZONE_A | 合法但再次错误禁止NAV，并可能把“禁止前往…”混入允许地点，转人工，F |
| 1051 另一合法对照 | “仅允许前往F2_ZONE_A，禁止使用CAP_INFO_DISPLAY能力。”；NAV到ZONE_A | 地点满足且未用禁用能力，实际完成，P |

反例索引`evidence/SRS_F022-V1.178-DEF-S3-116-final-counterexamples-20261107.json`包含定义原文、请求、三类校验/版本、SQL、事件、实际指令及同义对照；原始`http-20261107-mixed-clauses.json`和model-requests JSONL可重跑核对。语义依据是受控R07约束参与校验及原自然语言字段，不以实现的正则/分隔符定义期望，不为通过规定用户只能输入分号。分号/逗号对照的场景、能力、候选和模型目标夹具一致；脚本通用目标后缀含GATE的情况两者相同，实际候选targetLocation=ZONE_A且错误明确为禁止NAV，不是目标差异导致的判定。定位提示：当前按整段抽取禁止/仅允许极性，逗号未分离的混合维度可能互相套用，修复仍以业务预期验证。

原四反例与直接影响：1038短地点F2_TEST被拒绝、未冻结/下发，1039合法“仅允许使用NAV”完成；1053首次基线合法完成、1054模型503→实际试运行启用模板的禁区映射硬拒绝/未冻结/无指令；1056重规划基线合法尾部完成、1057真实前缀完成→失败重试/候选切换→局部重规划高风险转基线的禁区fallbackLocation尾部硬拒绝，前缀保留、基线不冻结、不下发禁区。自主重规划1046禁区拒绝，五步与完成条件/能力范围对照均当前通过。原四局部关闭不抵销本轮1049/1050，F013.R03受影响任务族约束子范围同证F，不增加执行次数或改写原历史验收。

执行：36去重业务组34P/2F；33任务1025～1057均HTTP创建，31业务任务、1052/1055两次成功试运行前置，无SQL伪造任务生命周期。19有效真实IAB组全P、20截图（包含一次更正的探针观察），0当前UI console error。UI看到产品错误清单的P仅证明正确展示，不冒充业务P。单轮`mvn -o test`460报告、458执行通过、2原有跳过、0失败/错误；`mvn -o package -DskipTests`及`npm run build`通过。实际打包JAR启动健康UP并完成认证/业务入口；独立打包类Spring容器构造成功，TaskDefinitionMapper与新增TaskMapper均实际注入，四服务对照P。模拟模型和设备协议不代表商业模型质量或真实物理设备验收。

探针更正：第一轮能力缺口的非法请求全400，但全表无变化快照与我授权的UI创建定义107重叠而误报F；暂停UI配置写入后复用当前夹具独立补测全P，原F保留。一次UI选项断言抢在路由/对话框转换完成前观察，截图显示对话框已关闭，fresh AX后明确重开确认P，原截图/行和更正保留。见probe-corrections及UI JSON；不将1049/1050产品F改称环境问题。其余HTTP探针无异常或缺失裁决；当前需求无NT，无历史P替代当前覆盖。首个产品F检查点已推送e3633c5，仍继续全部基线/重规划分支后才统一交修。

环境与清理：GPT schema tip_gpt_f006_v118_20261030、Redis10，18129后端、18117模型、15179 UI、18132～18135适配器；仅自有资源。全部33任务终态、失败版本/事件/指令保留，7定义DISABLED、2模板DISABLED、4自有设备INACTIVE，活跃分配/设备占用/触发器0；三预置业务字段及原JSON精确恢复，临时能力状态恢复，实际能力测试记录保留。停止自有3进程树，七端口释放；主工作区40用户文件哈希不变，不改产品、共享服务、Claude资源，不强推/reset或移动标签。原Office、凭据/令牌、JAR、DPAPI和无关用户文件不提交，公开日志临时口令脱敏。

正式裁决：规则R07、TC-068.S2仍F，其他七规则/三步骤当前P。证据先提交推送，再单写入者同步HANDOFF/ROADMAP/EXECUTION_BASELINE与无业务变更说明，填实际证据SHA。下一仅Claude接ai/gpt-test修116混合子句极性/作用域，保持本轮四原反例与117关闭行为，发布下一唯一标签后F022再整轮。main未合本轮、无PR，不提前推进F023，不代表后续、三核心或95项整体验收通过。
'''
assert len(state['definitionIds'])==7 and len(state['templateIds'])==2
(D/report).write_bytes(text.encode('utf-8'))
p=D/'阶段3-复测进度.md';s=p.read_text(encoding='utf-8');s+='\n\n2026-11-07 F022 V1.178整轮完成：READY_FOR_CLAUDE，规则7P/1F/0NT、四步骤3P/1F/0NT，36业务组34P/2F，全部当前实测/历史P复用0；原四反例P，116混合逗号约束1049/1050仍F，028/029/030/117保持关闭。33 HTTP任务、19有效IAB组/20保留截图，460报告458通过2原有跳过；配置/资源已清理，main保持413e1b3未合本轮、无PR。详见'+report+'与complete-verification索引；原F/探针更正保留，不推进F023。\n';p.write_bytes(s.encode('utf-8'))
print('Registered V178:36 business groups34P/2F; rules7P1F0NT; steps3P1F0NT; no main merge.')
