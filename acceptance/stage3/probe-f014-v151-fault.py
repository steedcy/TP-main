"""Invoke after starting the GPT backend in the named supervision failure mode."""
import importlib.util,json,sys
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f014-v151.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
mode=sys.argv[1];assert mode in ['UNDETERMINED','UNAVAILABLE']
cfg=p.l.API('配置管理员');op=p.l.API('运行操作员');ev=p.metadata();ev['mode']=mode;ev['definitionBefore']=cfg('/task-definitions/17')
marker='F151_FAULT_'+mode;cases={marker:{'steps':[p.step()],'confidence':.99,'diverse':False}};(r/'.local-test/f014-v151-cases.json').write_bytes(json.dumps(cases).encode())
try:
 cfg('/task-definitions/17/enable','POST');ev['request']={'taskGoal':marker+' synthetic service to F2_TEST_GATE','taskFamily':'EXT_0FA30230','sceneParams':{'targetLocation':'F2_TEST_GATE'}}
 t=op('/tasks','POST',ev['request']);o=p.observe(op,t['id']);ev['observed']=o
 ev['otherPages']={'dashboard':op('/dashboard/overview'),'tasks':op('/tasks?page=1&size=5'),'devices':cfg('/devices?page=1&size=10')}
 ev['checks']={'pendingManual':o['task']['status']=='PENDING_MANUAL','threePassAndFrozen':all(o['plans'][0][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']) and bool(o['plans'][0]['frozenAt']),'noDeviceCommandsOrAssignments':not o['commands'] and not o['assignments'],'errorRecorded':any(e['eventType']=='SUPERVISION_JUDGED' and (e.get('reasonCode')=='INJECTED_UNDETERMINED' if mode=='UNDETERMINED' else e.get('reasonCode')=='ERR_SUPERVISION_UNAVAILABLE') for e in o['events']),'otherPagesAvailable':all(x is not None for x in ev['otherPages'].values())}
 print(mode,t['id'],ev['checks'],flush=True)
finally:
 if ev['definitionBefore']['definitionStatus']=='DISABLED':cfg('/task-definitions/17/disable','POST')
 p.save('fault-'+mode.lower(),ev)
