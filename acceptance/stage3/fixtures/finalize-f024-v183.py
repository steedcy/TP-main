"""Finalize independent evidence/ledgers from preserved observations; no product edits.
This script does not write HANDOFF/ROADMAP/EXECUTION_BASELINE: those follow the
verified evidence push and use its actual commit SHA.
"""
import json,csv,hashlib,subprocess,re,collections,sys,socket
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parents[3];E=R/'acceptance/stage3/evidence';S=R/'acceptance/stage3'
PREFIX='SRS_F024-V1.183-';DATE='20261108';SHA='fc55f713e5d74d6fb41761f53fed84b4bc4efd7b'
REPORT='acceptance/stage3/SRS_F024-V1.183-整轮独立复测与统一交修.md'
RAW='acceptance/stage3/evidence/'+PREFIX+'http-sql-protocol-'+DATE+'.json'
INDEX='acceptance/stage3/evidence/'+PREFIX+'complete-verification-'+DATE+'.json'
ev=json.loads((R/RAW).read_text(encoding='utf8'));ui=json.loads((E/(PREFIX+'ui-observations-'+DATE+'.json')).read_text(encoding='utf8'))
def write(p,v):
 if not isinstance(v,str):v=json.dumps(v,ensure_ascii=False,indent=2)+'\n'
 p.write_text(v,encoding='utf8',newline='\n')
def run(args,cwd=R):return subprocess.check_output(args,cwd=cwd).decode('utf8').strip()
def append(p,line):
 t=p.read_text(encoding='utf-8-sig')
 if line not in t:write(p,t.rstrip()+'\n\n'+line+'\n')
by={r['name']:r for r in ev['cases']};now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
assert ev['productSha']==SHA and ev['configurationRestoration']['allRoundTasksTerminal']
assert all(ev['configurationRestoration'][k] for k in ['riskEnabledRestored','allOwnedDevicesInactive','allOwnedDevicesUnoccupied','taskDefinitionUnmodified'])
assert ev['configurationRestoration']['triggerCount']==0
assert by['cleanup']['checks']['historicalPendingUnchanged'] and by['cleanup']['checks']['noOccupied']
assert all(t['templateStatus']!='ENABLED' for t in ev['finalTemplates'])
ports=[18129,18117,15179,18132,18133,18134,18135,18136,18137]
for port in ports:
 with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',port))!=0,port
# Main user-file hashes are compared locally to the retained earlier manifest;
# publish only count/aggregate and the equality result, never user file names.
main=R.parent/'tip';names=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=main).decode('utf8').split('\0');hashes={n:hashlib.sha256((main/n).read_bytes()).hexdigest() for n in names if n and (main/n).is_file()}
prior=json.loads((R/'.local-test/main-untracked-before151.json').read_text(encoding='utf-8-sig'))
same=set(hashes)==set(prior) and all(hashes[k].lower()==str(prior[k]).lower() for k in hashes)
protected={'mainHead':run(['git','rev-parse','HEAD'],main),'trackedClean':not run(['git','status','--porcelain','--untracked-files=no'],main),'userUntrackedFileCount':len(hashes),'sameAsRetainedPreV151PerFileManifest':same,'aggregateSha256':hashlib.sha256(json.dumps(sorted(hashes.items()),ensure_ascii=False).encode()).hexdigest(),'pathsNotPublished':True}
assert protected['mainHead']=='9153fd97702c132efc83129bbc656d67ac36d6ac' and protected['trackedClean']
assert len(hashes)==40 and same,'Inspect real user file changes without overwriting them'
write(E/(PREFIX+'cleanup-and-main-preservation-'+DATE+'.json'),{'at':now,'productSha':SHA,'schema':ev['schema'],'redisDb':10,'stoppedOwnedPids':[12404,12028],'portsReleased':ports,'configurationRestoration':ev['configurationRestoration'],'historicalPendingRowsBefore':ev['initialPendingRows'],'historicalPendingRowsAfter':by['cleanup']['finalPendingRows'],'tasks':ev['finalTasks'],'devices':ev['finalDevices'],'templates':ev['finalTemplates'],'mainPreservation':protected})
issues={
 'DEF-S3-119':{'title':'非超规分支仍生成并冻结引导计划','level':'高','steps':'TC-073.S1;TC-073.S2','rules':'SRS_F024.R03','names':['goal-normal-no-guide','normal-model-false-missing'],'actual':'1104正常55×40×20cm/10kg只执行测量并COMPLETED，但自主版本108?实际id见raw仍含CAP_NAVIGATION与另外两后续步骤、后续分配SKIPPED；严格违反R03“不生成引导步骤”。事件正常1102无计划/指令合法对照P。1149原003反例已闭环，不抵销此计划生成偏差。','fix':'保留测量分支、阈值来源与正常完成；调整条件计划生成/冻结时机，使非超规结束不保留引导步骤；不能只把“不生成”改成“不下发”。'},
 'DEF-S3-120':{'title':'测量事件额外参数可覆盖计算事实且非正阈值未校验','level':'高','steps':'TC-072.S1;TC-073.S1','rules':'SRS_F024.R02','names':['event-extra-computed-override','event-invalid-dimensionThresholdCm-0','event-invalid-weightThresholdKg--1'],'actual':'1120输入length=55、weightThresholdKg=32，extraParams覆盖后持久化length=999、weightThresholdKg=0，而totalDimensionCm仍115、任务判定仍正常；1115/1116零尺寸阈值/负重量阈值HTTP200并建任务。事件记录的值、比较依据与判定缺乏一致性。','fix':'隔离/白名单化额外字段，禁止覆盖可信测量、临时号、阈值、判定与触发来源；校验有限正数阈值并记录真实部署来源，补合法边界和无副作用拒绝。'},
 'DEF-S3-121':{'title':'新模拟测量UI可见角色与事件接口权限不相容','level':'高','steps':'TC-072.S1;TC-073.S1','rules':'SRS_F024.R01','names':[],'actual':'生产dist真实浏览器：仅CONFIG_ADMIN可访问/simulators，新正常/超规按钮均POST /api/v1/tasks/measurement-event→403；OPERATOR/SYSTEM_ADMIN接口可用却无此页面路由，正常UI路径无法触发。既有API未授权403在请求校验前正确，不应删除既有权限门禁绕过。','fix':'对齐仿真事件合法操作者、页面路由与后端授权/受控仿真入口；保持正式任务写权限隔离；真实UI重测两样本、柜台缺省及输入拒绝。'},
 'DEF-S3-122':{'title':'测量恢复成功后后续步骤仍冻结而无法续跑','level':'高','steps':'TC-074.S1','rules':'SRS_F024.R04;SRS_F024.R08（场景流程依赖）','names':['measure-candidate-success','measurement-device-offline-recovery'],'actual':'1122测量失败一次重试后切备用，备用测量SUCCESS、STEP_COMPLETED/EXCEPTION_RECOVERED宣称计划可继续，但2/3/4仍FROZEN、任务持续EXECUTING超过探针40秒；1138测量执行中真实OFFLINE恢复同类。原始快照保留，取证后才人工终止。引导末步候选恢复1124为合法对照P。','fix':'恢复成功应按当前有效计划解冻合法未执行尾部并继续编排，保留原失败/测量结果/设备归属/重规划次数，不解冻已人工终止或其他任务步骤。'},
 'DEF-S3-123':{'title':'无可承接扫描器未生成能力缺口异常','level':'中','steps':'TC-074.S1','rules':'SRS_F024场景异常路径2a','names':['no-scanner'],'actual':'1136两扫描器协议OFFLINE，任务安全转PENDING_MANUAL、0业务指令且不虚构测量；但task_exceptions为空，只有PLAN_VALIDATED/基线不可用等通用事件，缺少要求的CAPABILITY_GAP异常与明确测量能力缺口。','fix':'记录可追溯的CAP_BAGGAGE_MEASURE缺口异常/原因和关联事件，并维持无虚构结果及安全转人工。'},
 'DEF-S3-124':{'title':'无移动资源未执行仅信息提示降级','level':'高','steps':'TC-076.S1','rules':'SRS_F024.R04；场景异常路径5b','names':['no-mobile'],'actual':'1137两机器人协议OFFLINE、扫描器和航显仍可用，计划因导航无候选整体失败并转人工，0测量/发布指令、未标注未完成引导；未按要求保留可用信息渠道执行。未虚报闭环的子断言P不等于本分支通过。','fix':'不扩大为运动控制；无移动资源时保留测量/上报/信息提示可用渠道并明确未完成引导，不能伪造完整闭环。'},
 'DEF-S3-125':{'title':'测量反馈缺三项必要数据仍可完成步骤或整任务','level':'高','steps':'TC-072.S1;TC-073.S1;TC-073.S2','rules':'SRS_F024.R02;SRS_F024.R08','names':['measurement-missing-dimensions','measurement-missing-weight','measurement-missing-oversize'],'actual':'1146仅measureStatus=SUCCESS/weight/isOversize=false、无尺寸，1147无重量，均HTTP200并COMPLETED；1148无isOversize也把测量步骤置COMPLETED并请求后续步骤。阈值富化不能替代缺失实测字段。','fix':'在业务完成条件前验证尺寸、重量、超规结果三项及可追溯依据，缺项应拒绝/失败恢复，不能推进下游或完成；保留真实失败反馈和合法完整对照。'}
}
# Remove an explanatory placeholder: the exact plan is already in each raw record.
issues['DEF-S3-119']['actual']=issues['DEF-S3-119']['actual'].replace('自主版本108?实际id见raw','自主冻结版本')
for iid,x in issues.items():
 write(E/(PREFIX+iid+'-minimal-'+DATE+'.json'),{'issue':iid,'title':x['title'],'productSha':SHA,'tag':'V1.183','expected':x['fix'],'actual':x['actual'],'rawObservations':[by[n] for n in x['names']],'uiObservations':[r for r in ui if 'role-denied' in r['name']] if iid=='DEF-S3-121' else [],'proxy403':[r for r in ev['network'] if r['http']==403 and 'measurement-event' in r['path']] if iid=='DEF-S3-121' else []})
privacyNames=['event-privacy-instructions','event-privacy-source','event-privacy-devicecode','event-private-instructions-oversize','goal-text-privacy','goal-privacy-top','goal-privacy-nested','goal-privacy-list','goal-privacy-json','clarification-privacy-top','clarification-privacy-json']
write(E/(PREFIX+'DEF-S3-032-minimal-'+DATE+'.json'),{'issue':'DEF-S3-032','productSha':SHA,'tag':'V1.183','canariesAreFictional':True,'actual':'1117/1118/1119新事件说明/来源/设备编码含身份文本可持久化；1151超规说明canary进入模型请求；1152自然语言目标canary虽被模型请求清理，仍在任务和GOAL_SUBMITTED事件保存。嵌套Map/List/JSON及澄清拒绝正对照P。','rawObservations':[by[n] for n in privacyNames]})
ruleDecisions={
 'R01':('F','两入口API、事件别名及实际操作员UI提交/澄清可运行；模拟控制台正常和超规按钮受121权限矛盾阻断。','DEF-S3-121'),
 'R02':('F','完整三项/158cm与32kg声明边界P；120额外参数覆盖事实，125缺尺寸/重量/超规结果仍完成测量。','DEF-S3-120;DEF-S3-125'),
 'R03':('F','正常测量后完成且仅一次测量指令P；1104仍生成冻结引导计划和SKIPPED后续，违反“不生成”原文。','DEF-S3-119'),
 'R04':('F','四渠道自主三类PASS/LOW执行、高风险合格基线和办理说明UI均P；1137无移动资源未执行可用信息提示降级。','DEF-S3-124'),
 'R05':('P','真实五动作1127完成，六动作1128在持久计划前以ERR_STEP_LIMIT_EXCEEDED拒绝；0下发。',''),
 'R06':('P','真实导航仅空间业务参数；运动安全speed反例1131未冻结/下发，其余三类拒绝及正确物理渠道P。',''),
 'R07':('P','引导一次重试、候选切换、一次局部重规划成功/失败转人工当前P；保留三已完成前序与版本，1153真实待人工UI。测量恢复故障单独归TC074，不冒充引导失败。',''),
 'R08':('F','完整超规闭环/步骤结果/完成时间/事件/进度UI当前P；1146/1147无必要测量数据仍COMPLETED，不能视为完整测量闭环记录。','DEF-S3-125'),
 'R09':('F','临时号及顶层/嵌套Map/List/JSON/澄清拒绝P；新事件文本说明等未保护，1151入模、1152目标/事件持久身份哨兵。','DEF-S3-032')}
stepDecisions={
 'TC-072.S1':('F','操作员/事件/别名、柜台缺省/空白/合法字段及边界均执行；120/125测量事实及032身份残留，121真实事件UI403。','DEF-S3-120;DEF-S3-125;DEF-S3-032;DEF-S3-121'),
 'TC-072.S2':('P','自主四渠道按测量→告警→智慧航显→机器人执行；三类校验/监督、实际高风险转经试运行合格基线、五步/六步边界与运动拒绝、办理说明/柜台真实UI通过。069与NT005当前闭环。',''),
 'TC-072.S3':('P','完整合法超规任务1103/1134/1140等结果/完成时间/每步状态/闭环事件、真实生产详情及两个版本切换P；未把缺项正常测量或无移动资源失败算为完整正例。',''),
 'TC-073.S1':('F','正常事件无计划/指令直接完成P；操作员测量分支仍生成冻结引导计划119，缺三项数据仍完成测量125。','DEF-S3-119;DEF-S3-125'),
 'TC-073.S2':('F','合法正常测量1104与原003反例1149正确完成/保留来源且无发布引导；1146/1147无尺寸或重量仍整任务完成，结果不完整。','DEF-S3-125'),
 'TC-074.S1':('F','测量失败一次重试成功P；候选/离线恢复成功后尾部仍FROZEN 122；两扫描器无候选转人工但无能力缺口异常123。','DEF-S3-122;DEF-S3-123'),
 'TC-075.S1':('P','引导失败一次重试/切备用、仍失败后单次局部重规划成功与失败转人工，前序结果保留；另补1153自然待人工UI，非重复冒增原观察次数。',''),
 'TC-076.S1':('F','两机器人OFFLINE、扫描器/航显在线，未发布信息而整体转人工；保留原失败，不把0虚构闭环子断言当整步P。','DEF-S3-124')}
def readcsv(p):
 with p.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);return r.fieldnames,list(r)
def writecsv(p,fields,data):
 with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(data)
def addold(row,key,new):
 if new and new not in row.get(key,''):row[key]=(row.get(key,'')+';'+new).strip(';')
fields,data=readcsv(S/'rules.csv')
for row in data:
 if row['requirement']=='SRS_F024':
  status,reason,iid=ruleDecisions[row['ruleId'].split('.')[-1]];row.update(status=status,verifiedBy='V1.183 current independent round / '+reason,issue=iid);addold(row,'evidence',RAW);addold(row,'evidence',REPORT)
writecsv(S/'rules.csv',fields,data)
fields,data=readcsv(S/'steps.csv')
for row in data:
 if row['stepId'] in stepDecisions:
  status,reason,iid=stepDecisions[row['stepId']];history=row.get('actual','')
  if 'V1.183 current round' not in history:row['actual']=history+'；V1.183 current round：'+reason
  row.update(status=status,observedAt=now,issue=iid);addold(row,'evidence',RAW);addold(row,'evidence',REPORT)
writecsv(S/'steps.csv',fields,data)
fields,data=readcsv(S/'issues.csv');print('issueColumns',fields)
keys={r['issueId']:r for r in data} if 'issueId' in fields else {r[fields[0]]:r for r in data}
def update_issue(iid,status,actual,proof,nextaction):
 row=keys[iid];row[fields[5]]=status;addold(row,fields[6],'2026-11-08 V1.183：'+actual);addold(row,fields[7],proof);row[fields[8]]=nextaction
update_issue('DEF-S3-003','CLOSED V1.183当前原反例/合法对照通过（历史失败保留）','1105超规及1149正常样本均在模型虚假缺失时INFO_CHECK_OVERRIDE，不追问身份/不重复三轮，完成预期测量/四渠道。R03新119独立保留。',RAW+';'+REPORT,'保持已给位置/真正缺失位置及合法补充回归；不以003关闭替代R03或整项通过。')
update_issue('DEF-S3-032','F024 V1.183仍F；F010历史关闭证据保留','1117/1118/1119事件文本身份未拒绝入库，1151办理说明入模，1152自然语言目标/事件持久身份哨兵；递归结构及澄清当前拒绝P。', 'acceptance/stage3/evidence/'+PREFIX+'DEF-S3-032-minimal-'+DATE+'.json;'+REPORT,'统一目标/场景参数/事件DTO全部可持久字段及澄清的身份保护，临时号合法对照不误拒；HTTP/DB/事件/模型请求重新整轮实测。')
update_issue('DEF-S3-069','CLOSED V1.183 F024四渠道完整闭环当前实测通过','1103自主四能力正确物理渠道、三类PASS/LOW，1140真实UI提交并实际四步完成，1134高风险合格基线实际四步完成及真实UI版本；当前关闭预置能力矛盾，不掩盖其他场景失败。',RAW+';'+REPORT,'保持正确扫描器/智慧航显/机器人分工；124无移动降级为独立根因，不能将缺资源当069历史配置矛盾。')
update_issue('NT-S3-004','本轮前置已执行；UI产品F转DEF-S3-121','事件两个API/别名、正常/超规与柜台缺省合法边界本轮已执行；实际仿真UI正常和超规均403，登记121，当前无未执行NT。',RAW+';'+REPORT,'修121并在新标签整轮真实UI与API复测。')
update_issue('NT-S3-005','CLOSED V1.183办理说明与高风险独立分支当前已补齐','真实1103/1140办理说明/柜台/临时号/测量/事件；1134高风险版本及已执行合格基线UI，试运行1133真实四渠道反馈SUCCESS。',RAW+';'+REPORT,'保持办理说明UI和不同监督风险分支，不以本缺口关闭替代整项通过。')
for iid,x in issues.items():
 if iid in keys:raise AssertionError('new issue identifier already exists: '+iid)
 row=dict(zip(fields,[iid,'缺陷',x['level'],x['steps'],x['rules'],'待Germini修复（V1.183本轮实测F）',x['actual'],'acceptance/stage3/evidence/'+PREFIX+iid+'-minimal-'+DATE+'.json;'+REPORT,x['fix']]))
 data.append(row);keys[iid]=row
writecsv(S/'issues.csv',fields,data)
business=[r for r in ev['cases'] if r['name'] not in ['resources-ready','cleanup'] and r.get('result') in ['P','F']]
counts=collections.Counter(r['result'] for r in business);statuses=collections.Counter(t['status'] for t in ev['finalTasks'])
index={'requirement':'SRS_F024','productSha':SHA,'tag':'V1.183','handoffSha':'c7cd6b3696cfc8d18813778d2b9bf74d7f27286b','baseline':'V2.4','timezone':'Asia/Shanghai','at':now,'status':'READY_FOR_CLAUDE','actualReceiver':'Germini','checkpointSha':'5f18f28c3a9fd1f4b0e9709050b2e25d7bf04bc4','rules':{k:{'status':v[0],'basis':v[1],'issues':v[2]} for k,v in ruleDecisions.items()},'steps':{k:{'status':v[0],'basis':v[1],'issues':v[2]} for k,v in stepDecisions.items()},'ruleCounts':dict(collections.Counter(x[0] for x in ruleDecisions.values())),'stepCounts':dict(collections.Counter(x[0] for x in stepDecisions.values())),'rawObservationCounts':{'businessPF':dict(counts),'businessPFCount':len(business),'exploratoryExcluded':1,'resourceChecks':2,'uiSavedGroups':len(ui),'persistentTasks':len(set(ev['taskIds'])),'realProtocolTrialTasks':1,'taskFinalStates':dict(statuses),'noHistoricalBusinessPSubstitution':True,'layersNotAddedAsSeparateBusinessExecutions':True},'issues':['DEF-S3-032']+list(issues),'closedOriginalIssues':['DEF-S3-003','DEF-S3-069','NT-S3-005'],'executedOriginalGapWithNewF':{'NT-S3-004':'DEF-S3-121'},'raw':RAW,'report':REPORT,'modelJournal':'acceptance/stage3/evidence/'+PREFIX+'model-journal-'+DATE+'.jsonl','build':'acceptance/stage3/evidence/'+PREFIX+'build-version-'+DATE+'.json','cleanup':'acceptance/stage3/evidence/'+PREFIX+'cleanup-and-main-preservation-'+DATE+'.json','main':protected,'noMainMergeOrPR':True,'limitations':['Controlled model and five protocol simulators, not commercial-model or physical-device certification','Backend 490 tests: 487 passed, 1 existing test-contract error, 2 skipped; preserved, not reported as full pass','Only final browser page console summary is zero errors; no claim that intentional 403 requests were successful'],'probeCorrections':['reasonCode/eventType confusion corrected from same raw observation','six-step early count rejection uses event before plan persistence','unused required baggageLocation template input removed after failed fixture creation, then real qualified trial completed','guessed counter enumeration excluded; original F retained in explorationAdjudication'],'formalHandoffPolicy':'Push/verify complete evidence first; then write HANDOFF/ROADMAP/EXECUTION_BASELINE with actual evidence commit SHA. Remain on F024; no F025 or Gemini UI actions in this chat.'}
write(R/INDEX,index)
issueRows='\n'.join('| '+iid+' | '+x['title']+' | '+x['actual']+' |' for iid,x in issues.items())
ruleRows='\n'.join('| '+k+' | '+v[0]+' | '+v[1]+' |' for k,v in ruleDecisions.items())
stepRows='\n'.join('| '+k+' | '+v[0]+' | '+v[1]+' |' for k,v in stepDecisions.items())
report=f'''# SRS_F024 V1.183 整轮独立复测与统一交修

本轮未通过，统一交Germini修复。正式规则 **3P/6F/0NT**，TC072～076八步骤 **3P/5F/0NT**。当前需求全部适用分支已实测，未因首F停止；无历史业务P替代当前观察，无产品源码修改、无main合入或PR。当前main仍`{protected['mainHead']}`。

固定产品`{SHA}` / **V1.183**；修复方正式交接`c7cd6b3696cfc8d18813778d2b9bf74d7f27286b`已快进合入ai/gpt-test。远端附注标签对象`93b5beb6c8d410ce86d357d1044dd692767fb6e4`解引用精确等于产品SHA，未移动。执行/用例V2.4，Asia/Shanghai。证据检查点`5f18f28c3a9fd1f4b0e9709050b2e25d7bf04bc4`已先推送；完整证据提交的实际SHA由随后正式HANDOFF记录，不用自引用占位SHA。

## 正式规则与步骤

| 规则 | 当前 | 完整裁决 |
| --- | --- | --- |
{ruleRows}

| 步骤 | 当前 | 完整裁决 |
| --- | --- | --- |
{stepRows}

R07限定原文“引导失败”，其所有恢复分支本轮P；测量恢复/无扫描器问题准确列TC074及场景异常路径，不把无依赖的引导P改F。R08不能把1146/1147的缺项正常测量完成当完整测量记录。各P仅为所列规则/步骤，不代表整项或95项通过。

## 统一缺陷清单

**DEF-S3-032仍F**：1117/1118/1119新事件的办理说明/来源/设备编码身份文本入库，1151超规说明canary进入模型，1152目标文本canary保存在任务与提交事件，模型请求虽已清理仍不满足“不保存”。所有canary均虚构。顶层、嵌套Map/List/JSON及澄清拒绝当前P，原F010关闭证据保留，不以其替代F024。

| 编号 | 偏差 | 原始事实 |
| --- | --- | --- |
{issueRows}

每项最小证据为`evidence/{PREFIX}DEF-S3-xxx-minimal-{DATE}.json`，包含预期/实际和原始HTTP/SQL/计划/事件/协议报文；121另含真实UI观察和生产代理403记录。修复要求在issues.csv中逐项列明。003原“已有位置却三轮误缺失”当前由1105/1149超规/正常模型反例关闭；069四渠道预置矛盾及NT005高风险/办理说明缺口关闭；NT004全部补执行后发现121产品F，当前不留未执行NT。

## 当前实测与层级

- {len(set(ev['taskIds']))}个持久任务：51个正式/边界/恢复任务、1个实际四渠道基线试运行1133；全部真实HTTP创建，未SQL伪造任务状态。最终状态{dict(statuses)}，失败原记录保留。
- 去除2个资源检查及1个无正式枚举依据的探索后，**{len(business)}个去重HTTP/SQL/协议业务观察组，{counts['P']}P/{counts['F']}F**。一个观察映射多规则/步骤不增加次数；UI与API不叠加为额外业务执行。1153为补充自然待人工页面断言而新增的独立生命周期，原因已写探针。
- 真实生产dist浏览器{len(ui)}个保存组：三角色登录、实际操作员目标提交/位置补充/四渠道完成、正常/超规结果、办理说明/柜台/临时号、两个高风险版本切换、局部重规划与自然待人工。配置管理员正常/超规仿真事件按钮均403。当前最后页面console摘要为空，不宣称全轮所有故障请求零错误。
- 有限恢复：测量一次重试P、测量候选/离线恢复122 F；引导重试/候选/一次局部重规划成功/失败转人工全部P。无扫描器无虚构测量P但缺异常123 F；无移动信息降级124 F。原完成前序、版本、指令及时间线取证完整。
- 实际三类校验/监督LOW及HIGH、五动作有效边界/六动作拒绝、结构/能力/运动参数/缺展示渠道反例均测。三类拒绝无未校验物理业务命令，正确扫描器/智慧航显/移动机器人渠道通过。只运行五个GPT协议仿真体和受控模型；不扩大为商业模型或真实物理设备认证。

## 构建、版本和口径

本轮固定新源码重新执行`mvn -o test`：490项，487通过、1错误、2原有跳过。唯一错误`GoalClarificationRoundsTest.keepsAllAnswersAndStopsAfterThreeIncompleteRounds:59`沿用原问题回答，新RequiredInfoGuard已换成必要信息问题，第二轮被拒。保留原失败栈交修维护，不以定向40项或构建成功冒称全量通过；自然当前问题补充1139/1140已经真实HTTP/UI通过，故不把该旧测试契约差异另造产品运行缺陷。

`mvn -o package -DskipTests`与`npm run build`均成功。新JAR SHA256 **81ed55f93dd22db3f0e2bc9167f7a2f2c37a4a84a7933f7b86e2f1af0a6a9b26**，本轮实际启动健康UP/认证/全部业务入口；未复用F023旧JAR。前端构建3m24s，只有既有chunk大小提示。构建/文件清单见build-version JSON。

交接20kg/23kg内部不一致：当前实现默认23kg，边界23/23.001本轮核对；正式stage0按“部署阈值及来源”，AC017保留158cm/32kg样本。本轮声明158cm/32kg、`SYNTHETIC_DEPLOYMENT_F024_158CM_32KG`虚构部署来源测试闭边界和略超，不将任何默认“2026版”文字认证为真实航空标准。没有修改业务基线。R03仍按“不生成引导步骤”裁决，不以既有SKIPPED实现回溯改为“不下发”。

探针错误不交产品修复：闭环reasonCode误看作eventType、六步在计划持久化前被拒的阶段差异，均从同版原始观察更正且保留旧检查；模板未使用的必填baggageLocation导致400已移除后重新通过实际合格试运行；猜测柜台字符串枚举无stage0明细依据，原F保留为OBS排除，合法/缺省/空白及对象错误类型另有实际观察，不虚构白名单。检查点与当前原始记录均保留。

## 资源与交接

GPT schema `{ev['schema']}` / Redis10。开工无其他Java/Python业务进程和七原测试端口监听；加入备设备前也核查18136/18137。历史20个非删除设备名额占满，为保留档案，第二次自有JAR启动临时配置注册名额21，仅运行五个仿真体；这不是F003容量验收，也不修改产品或数据库历史档案。进程停止后该覆盖撤销。

所有52任务保留并收为COMPLETED/MANUAL_TERMINATED；模板99已停用，五设备INACTIVE、全部占用0、本轮活跃分配0，26条历史PENDING_ASSIGNMENT/EXECUTING行逐项保持，风险enabled及设备/能力原配置恢复、预置任务定义完全未改、注入触发器0。真实测试/配置版本审计保留。确认命令行归属后停止自有JAR12404/Python12028，九端口全部释放。原首次JAR1200仅用于启动UP和容量前置，随后正常停止后以同一JAR重启，不混版。

main跟踪文件干净，40用户未跟踪文件逐一与留存开工前清单哈希一致，不上传其路径或原Office。未操作Germini客户端/其worktree、共享PG/Redis服务或其他AI资源。先完整证据提交推送并实核，再由本对话单写HANDOFF/ROADMAP/EXECUTION_BASELINE记录实际证据SHA为READY_FOR_CLAUDE（实际接收者Germini）；不合main、不启动F025。总索引`{INDEX}`；主原证据`{RAW}`。
'''
write(R/REPORT,report)
append(S/'阶段3-复测进度.md',f'''## 2026-11-08 F024 V1.183整轮完成并统一交修

产品`{SHA}` / V1.183，正式修复交接c7cd6b3696cfc8d18813778d2b9bf74d7f27286b；规则3P/6F/0NT、TC072～076八步骤3P/5F/0NT。52真实任务含1试运行，83业务观察67P/16F、1探索排除、2资源检查，10真实UI保存组；无历史业务P替代。003/069/NT005当前闭环，NT004补执行后121 F；032及新增119～125统一交Germini。生产构建/新JAR UP，490报告487通过/1旧澄清测试契约错误/2原跳过，失败原栈保留。所有自有资源恢复，九端口释放、26历史分配行未变、40用户文件哈希未变。main保持9153fd97702c132efc83129bbc656d67ac36d6ac，未合/无PR、不推进F025。报告`{REPORT}`，总索引`{INDEX}`；先完整证据推送实核，再正式HANDOFF记实际SHA。''')
# Normalize only this round's new text to LF; preserve JSON values and all failures.
for p in list(S.glob(PREFIX+'*.md'))+list(S.glob('probe-f024-v183*.py'))+list((S/'fixtures').glob('*f024-v183*.py'))+list(E.glob(PREFIX+'*.json'))+list(E.glob(PREFIX+'*.jsonl')):
 raw=p.read_bytes();p.write_bytes(raw.replace(b'\r\n',b'\n'))
print(json.dumps({'ruleCounts':index['ruleCounts'],'stepCounts':index['stepCounts'],'observations':index['rawObservationCounts'],'mainPreservation':protected},ensure_ascii=False))
