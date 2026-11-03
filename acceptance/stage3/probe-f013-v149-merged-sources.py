"""Isolate definition constraints without duplicating a machine assertion in the raw goal."""
import importlib.util,json
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v149.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
op=p.l.API('运行操作员');cfg=p.l.API('配置管理员');ev=p.metadata();ev['cases']=[]
old=json.loads((r/'acceptance/stage3/evidence/SRS_F013-V1.145-baseline-and-manual-actions-20261103.json').read_text(encoding='utf-8'))
ev['definition']=cfg(f"/task-definitions/{old['definition']['id']}")
controlled=json.loads((r/'.local-test/f013-v149-cases.json').read_text(encoding='utf-8'))
for marker,positive in [('F149_NATURAL_GOAL',False),('F149_MODEL_OVERRIDE',False),('F149_MODEL_GOOD',True),('F149_DUPLICATE_STEP',False),('F149_REVERSE_DUP',False),('F149_EQUAL_DUP',True),('F149_LEGAL_AND',True)]:
 req={'taskGoal':marker+' synthetic navigation to F2_TEST_GATE','taskFamily':ev['definition']['definitionCode'],'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
 t=op('/tasks','POST',req);tid=t['id'];o=p.observe(op,tid);v=o['plans'][-1]
 if positive:checks={'threePass':all(v[k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'frozen':bool(v['frozenAt']),'supervised':any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events'])}
 else:checks={'constraintRejected':v['constraintCheckResult']=='FAIL','conflictCode':any(e['reasonCode']=='ERR_COMPLETION_CONDITION_CONFLICT' for e in v['validationErrors']),'notFrozen':not v['frozenAt'],'notSupervisedOrDispatched':not any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events']) and not o['commands'] and not o['assignments']}
 case={'name':marker,'request':req,'controlledResponse':controlled[marker],'observed':o,'checks':checks}
 if marker=='F149_DUPLICATE_STEP':
  case['forceAttempts']=[]
  for action in ['FORCE_RELEASE','REQUEST_SUPERVISION']:
   before=p.observe(op,tid);res=p.raw(op,f'/tasks/{tid}/manual-actions',{'action':action,'reason':'F013 V149 synthetic hard-gate audit regression'});after=p.observe(op,tid)
   gateChecks={'http400code4110':res['http']==400 and res['body'].get('code')==4110,'pendingManual':after['task']['status']=='PENDING_MANUAL','noDispatch':not after['assignments'] and not after['commands'],'plansUnchanged':before['plans']==after['plans'],'newInterceptionEvent':sum(e['eventType']=='FORCE_BYPASS_INTERCEPTED' for e in after['events'])==sum(e['eventType']=='FORCE_BYPASS_INTERCEPTED' for e in before['events'])+1,'newInterceptionAudit':len(after['bypassAuditRows'])==len(before['bypassAuditRows'])+1 and after['bypassAuditRows'][-1].endswith('|INTERCEPTED')}
   case['forceAttempts'].append({'action':action,'response':res,'after':after,'checks':gateChecks});print(action,gateChecks,flush=True)
 if o['task']['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:case['cleanupTerminate']=p.raw(op,f'/tasks/{tid}/terminate',{'reason':'F013 V149 source-isolation fixture cleanup','confirmed':True})
 ev['cases'].append(case);p.save('merged-sources-definition-priority',ev)
 print(json.dumps({'case':marker,'taskId':tid,'checks':checks}),flush=True)
