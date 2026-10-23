import importlib.util, json, pathlib, shutil, datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
E=ROOT/"document/formal-test-evidence"
spec=importlib.util.spec_from_file_location("localenv",ROOT/"scripts/local-test-environment.py")
env=importlib.util.module_from_spec(spec);spec.loader.exec_module(env)
ids=["TC-035","TC-036","TC-037","TC-041","TC-045","TC-046","TC-047","TC-061"]
r03=json.loads((E/"R03-results.json").read_text(encoding="utf-8"))
payload={"batch":"R06","executionDate":"2026-10-23","timezone":"Asia/Shanghai","tester":"Codex（自动执行）","scope":ids+["TC-052"],"results":r03["results"]}
def item(code): return next(x for x in payload["results"] if x["id"]==code)
item("TC-035")["steps"][1]["note"]=("R06真实Kimi任务201首次快照后尝试将两台机器人置离线，但设备仍持续报告ONLINE；Kimi计划因安全字段及任务族未声明CAP_ESCORT被校验拒绝，系统转入基线并生成第二快照，未触发原计划局部重规划。新旧快照未体现受控设备状态变化，故该步骤仍NT。注入与恢复记录、两次快照和计划版本见R06-TC035-replan-context.json。")
item("TC-037")["steps"][0]={"result":"NT","note":"R06真实Moonshot/Kimi任务200生成自主候选计划V1，含目标、5个动作步骤、能力、参数、前置条件、完成条件和失败处理；上下文快照含代理能力/在线/位置/负载及时间。但计划说明、候选设备展示、参数来源标注和详情页呈现未逐项实测；V1未通过约束校验，故不以基线版本补证这些展示项。证据：R06-TC037-live-kimi.json。"}
item("TC-037")["steps"][1]={"result":"F","note":"真实Kimi任务200的自主V1包含5个动作，但第3步带‘路径点’运动安全字段，第5步使用任务定义未声明的CAP_ESCORT；计划校验记录ERR_MOTION_SAFETY_FIELD与ERR_CAPABILITY_NOT_IN_TASK_DEFINITION，constraintCheckResult=FAIL，未冻结且未执行该版本。随后转已校验基线执行。原步骤要求只引用已启用能力且通过校验后冻结，实测不符，记F。条件节点/分支计数本次未覆盖。证据：R06-TC037-live-kimi.json。"}
item("TC-041")["steps"][2]["note"]="R06任务200的自主失败计划被硬校验拦截，未观察到该版本进入监督、分配或下发；平台随后使用通过校验的基线完成任务。没有对失败版本尝试监督/人工强行放行，也没有业务入口证据证明拒绝记录，故指定分支仍NT。证据：R06-TC037-live-kimi.json、B05-results.json、B06-results.json。"
item("TC-046")["steps"][0]["note"]="既有任务187/188/189及190的GOAL_CLARIFIED.reasonCode均为INFO_INCOMPLETE，并有待补充问题；PLANNING且无快照/计划是等候澄清的正常流程，不构成监督不可用、超时或规划故障证据。R06任务201按原问题补充后reasonCode为空并继续规划，但未注入监督无法确定/不可用/超时，故仍NT。证据：R03-TC037-kimi-five-action.json、R03-post-restart-kimi.json、R04-health-check.json、R06-TC035-replan-context.json。"
item("TC-046")["steps"][1]["note"]="R06任务200观察到自主计划因安全字段和任务族能力约束未通过校验，事件记录ERR_VALIDATION_FAILED并转基线；该失败计划未进入监督判定。未对未通过三类校验的版本调用监督或人工放行，故本分支仍NT。证据：R06-TC037-live-kimi.json、B05-results.json、B06-results.json。"
item("TC-047")["steps"][0]["note"]="合并B06对高风险、规划失败、模型不可用的自动基线选择记录。R06任务200另观察到自主计划约束校验失败后自动转入已校验基线并完成任务。校验页面主动转基线分支仍未实测，故该步NT；此前R03/R04模型INFO_INCOMPLETE等待澄清不作为规划故障证据。证据：B06-results.json、R06-TC037-live-kimi.json、R03-post-restart-kimi.json、R04-health-check.json。"
item("TC-047")["steps"][1]["note"]="现有原启用基线仍分别对应不同任务族；未构造同族多模板组，精确任务族、步骤数及最近试运行通过时间优先级均未实测。R06任务200只观察到任务约束校验失败后选择唯一匹配基线，不能据此推定排序。证据：R03-precheck.json、R03-final-environment.json、R06-TC037-live-kimi.json。"
item("TC-061")["steps"][0]["note"]="合并B08实测：剩余额度3时本地规划故障夹具返回4个替换动作，平台拒绝且未保存或下发；剩余额度0分支仍未触发。R06真实Kimi任务未进入执行故障重规划，故本步骤继续NT。证据：B08-TC061-over-quota.json、B08-results.json、R03-final-environment.json、R06-TC037-live-kimi.json。"
item("TC-061")["steps"][1]["note"]="B08留有重试、失败和动作分配事件，但替换计划超额后未保存；重试/失败动作计数、条件节点与分支计数及后续方案总动作上限未整体覆盖。R06没有补足这些执行重规划分支。证据：B08-TC061-over-quota.json、R06-TC037-live-kimi.json。"
r04=json.loads((E/"R04-results.json").read_text(encoding="utf-8")); tc52=next(x for x in r04["results"] if x["id"]=="TC-052")
tc52["steps"][1]["note"]="B07任务103在分配前因全部机器人离线而被能力校验拦截，未覆盖分配阶段全部候选主动拒绝；R04任务190的原始GOAL_CLARIFIED.reasonCode为INFO_INCOMPLETE，属于目标理解等待补充信息，未到达快照/分配。没有把离线或等待补充信息当成全拒绝，故该分支仍NT。证据：B07-TC052-no-candidate.json、R04-health-check.json。"
payload["results"].append(tc52)
counts={x:sum(1 for r in payload["results"] if r["conclusion"]==x) for x in ("P","F","NT")}
payload["summary"]=counts
(E/"R06-results.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

# Final live-state capture: no credentials or device secrets are written.
agents=env.API()("/device-agents?page=1&size=100")["content"]
templates=env.API()("/baseline-templates")
simulators=env.API()("/simulators")
operator=env.API("运行操作员")
tasks=[]
for tid in (200,201):
 t=operator(f"/tasks/{tid}");tasks.append({"id":t.get("id"),"taskCode":t.get("taskCode"),"status":t.get("status"),"failureReason":t.get("failureReason")})
log=ROOT/".local-test/backend.log";call_lines=[]
if log.exists():
 for line in log.read_text(encoding="utf-8",errors="ignore").splitlines()[-1200:]:
  if "MoonshotChatClient" in line and "Kimi model=" in line:
   # Retain model-call metadata only; never retain request or credential strings.
   call_lines.append(line.strip()[:300])
final={"recordedAt":env.stamp(),"provider":"Moonshot/Kimi (verified by live tasks 200/201 and backend model-call metadata)","modelCallMetadata":call_lines[-12:],
 "originalSixAgents":[{k:a.get(k) for k in ("agentId","deviceCode","agentStatus","onlineStatus","workStatus","currentTaskId")} for a in agents if a.get("deviceCode") in {"SIM_F2_DISPLAY","SIM_F2_BAGGAGE","SIM_F2_FLIGHT","SIM_F2_ROBOT","SIM_F2_BAGGAGE_B","SIM_F2_ROBOT_B"}],
 "originalThreeBaselines":[{k:t.get(k) for k in ("id","templateName","templateStatus","templateVersion","isPreset")} for t in templates if t.get("isPreset")],
 "simulatorModes":[{k:s.get(k) for k in ("deviceCode","onlineStatus","scenarioResult")} for s in simulators if s.get("deviceCode") in {"SIM_F2_DISPLAY","SIM_F2_BAGGAGE","SIM_F2_FLIGHT","SIM_F2_ROBOT","SIM_F2_BAGGAGE_B","SIM_F2_ROBOT_B"}],
 "r06Tasks":tasks,"tc035OfflineRestored":True,"tc091Executed":False,"shutdownPerformed":False}
env.save(E/"R06-final-environment.json",final)
print(json.dumps({"summary":counts,"agentStatuses":[(a.get("deviceCode"),a.get("onlineStatus"),a.get("workStatus"),a.get("currentTaskId")) for a in final["originalSixAgents"]],"baselines":[(t.get("templateName"),t.get("templateStatus")) for t in final["originalThreeBaselines"]],"tasks":tasks,"modelCallCount":len(call_lines[-12:])},ensure_ascii=False))
