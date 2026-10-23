"""R06 TC-035 live context change and controlled offline injection."""
import importlib.util, json, pathlib, threading, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("localenv",ROOT/"scripts/local-test-environment.py")
env=importlib.util.module_from_spec(spec);spec.loader.exec_module(env)
operator=env.API("运行操作员");admin=env.API("配置管理员")
OUT=ROOT/"document/formal-test-evidence/R06-TC035-replan-context.json"
request={"taskGoal":"请处理完全虚构航班 TESTR35 登机口变更：TESTR35 于 21:00 从 F2_TEST_GATE_A 变更至 F2_TEST_GATE_B，原因设备维护。向旅客发布变更并规划无障碍引导；只使用已登记业务能力，不下发运动控制指令。全部数据虚构。",
 "taskFamily":"FLIGHT_CHANGE_RESPONSE","sceneParams":{"flightNumber":"TESTR35","updateType":"GATE_CHANGE","updateContent":"虚构航班TESTR35由F2_TEST_GATE_A改为F2_TEST_GATE_B，21:00生效，原因设备维护","displayDuration":60,"targetLocation":"F2_TEST_GATE_B","routePreference":"BARRIER_FREE"}}
result={"recordedAt":env.stamp(),"provider":"Moonshot/Kimi","request":request,"injectedDevices":["SIM_F2_ROBOT","SIM_F2_ROBOT_B"],"offlineActions":[],"clarificationRounds":[]}
task=operator("/tasks","POST",request);tid=task["id"];result["taskId"]=tid
def snap(): return operator(f"/tasks/{tid}/context-snapshots")
def events(): return operator(f"/tasks/{tid}/events")
deadline=time.monotonic()+150
rounds=0;offline=False
try:
 while time.monotonic()<deadline:
  current=operator(f"/tasks/{tid}");qs=current.get("missingInfoQuestions") or []
  if current.get("status")=="PLANNING" and qs and rounds<3:
   answers={q:("虚构航班TESTR35，21:00从F2_TEST_GATE_A变更至F2_TEST_GATE_B，原因设备维护；旅客从F2_TEST_GATE_A前往新登机口；只用登记的业务能力。") for q in qs}
   result["clarificationRounds"].append({"questions":qs,"answers":answers,"response":operator(f"/tasks/{tid}/clarify","POST",{"answers":answers})});rounds+=1;continue
  if not offline and any(e.get("eventType")=="CONTEXT_SNAPSHOT_GENERATED" for e in events()):
   result["firstSnapshot"]=snap()[-1]
   for code in result["injectedDevices"]:
    result["offlineActions"].append({"deviceCode":code,"response":admin(f"/simulators/{code}/online","POST",{"onlineStatus":"OFFLINE"})})
   offline=True
  if current.get("status") not in {"PLANNING","SUPERVISING","PENDING_ASSIGNMENT","EXECUTING","DOWNGRADING"}:
   break
  time.sleep(0.5)
 result["final"]={"task":operator(f"/tasks/{tid}"),"contextSnapshots":snap(),"planVersions":operator(f"/tasks/{tid}/plan-versions"),"events":events(),"stepAssignments":operator(f"/tasks/{tid}/step-assignments")}
finally:
 for code in result["injectedDevices"]:
  try: result.setdefault("onlineRestore",[]).append({"deviceCode":code,"response":admin(f"/simulators/{code}/online","POST",{"onlineStatus":"ONLINE"})})
  except Exception as ex: result.setdefault("onlineRestoreErrors",[]).append({"deviceCode":code,"error":str(ex)})
env.save(OUT,result)
print(json.dumps({"taskId":tid,"status":result.get("final",{}).get("task",{}).get("status"),"clarificationRounds":rounds,"snapshots":len(result.get("final",{}).get("contextSnapshots",[])),"offlineInjected":offline,"replanEvents":[e.get("eventType") for e in result.get("final",{}).get("events",[]) if e.get("eventType") in ("REPLANNING_TRIGGERED","CONTEXT_SNAPSHOT_GENERATED","REPLAN_SUCCEEDED")],"restoreErrors":result.get("onlineRestoreErrors",[]),"evidence":str(OUT)},ensure_ascii=False))
