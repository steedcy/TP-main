"""V2.4 full independent F021 HTTP/SQL/protocol round; synthetic model/adapters.
Fixed V1.174. Never alters product sources. Uses GPT-owned reusable schema.
"""
import importlib.util,json,time,copy,os
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('probe-f021-v174-base.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
q=m.Probe()
def st(seq=1,timeout=180,**kw):
 x=m.p.step(seq=seq,params={'targetLocation':'F2_TEST_GATE'});x.update(stepGoal='前往区域',completionCondition='routeGenerated=true',stepTimeout=timeout);x.update(kw);return x
def wait(fn,seconds=20):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.15)
 raise TimeoutError('Condition not observed')
def obs(row,key='after'):
 time.sleep(.2);row[key]=q.observe(row['taskId']);q.save();return row[key]
def event(o,t):return [e for e in o['events'] if e['eventType']==t]
def cfgcase(row,**kw):
 marker=row['request']['taskGoal'].split()[0];q.cases[marker].update(kw);(R/'.local-test/f021-v174-cases.json').write_text(json.dumps(q.cases),encoding='utf-8')
def msgs(row,typ):
 code=q.op(f'/tasks/{row["taskId"]}')['taskCode'];return [(d,x['message']) for d in q.devices for x in d.messages_for(code,typ)]
def accept(row):
 def pending():
  arr=q.op(f'/tasks/{row["taskId"]}/step-assignments');return next((x for x in arr if x['stepStatus']=='PENDING_ASSIGNMENT' and x.get('commandId')),None)
 a=wait(pending);code=q.op(f'/tasks/{row["taskId"]}')['taskCode']
 d=wait(lambda:next((d for d in q.devices if any(x['message']['commandId']==a['commandId'] for x in d.messages_for(code,'TASK_ACCEPT'))),None))
 msg=next(x['message'] for x in d.messages_for(code,'TASK_ACCEPT') if x['message']['commandId']==a['commandId']);ret=q.response(d,msg);row.setdefault('accepts',[]).append({'request':msg,'response':ret})
 executeId=m.sql(f"select execute_command_id from {m.SC}.task_step_assignments where task_id={row['taskId']} and command_id={m.lit(a['commandId'])}")
 return d,wait(lambda:next((mm for dd,mm in msgs(row,'EXECUTE_CAPABILITY') if dd==d and mm['commandId']==executeId and mm['attemptNo']==0),None))
def feed(row,d,msg,result='SUCCESS',reason=None,output=None):
 # Adapter receipt precedes transaction commit. Wait for durable attempt record
 # before the synthetic callback; retained 621 early-404 is fixture diagnostics.
 wait(lambda:int(m.sql(f"select count(*) from {m.SC}.device_commands where command_id={m.lit(msg['commandId'])} and attempt_no={int(msg['attemptNo'])}"))>0)
 with d.guard:
  body={'commandId':msg['commandId'],'attemptNo':msg['attemptNo'],'executionResult':result,'outputParams':output or {'routeGenerated':True}}
  if reason:body['reasonCode']=reason
  if result=='SUCCESS':d.state['workStatus']='IDLE'
  ret=d.report('EXECUTION_FEEDBACK',body);row.setdefault('feedbacks',[]).append({'agent':d.agent,'request':body,'response':ret});q.save();return ret

def failtwice(row,d,msg,result='FAILED',reason='ERR_SYNTHETIC_HARDWARE'):
 feed(row,d,msg,result,reason);retry=wait(lambda:next((mm for dd,mm in msgs(row,'EXECUTE_CAPABILITY') if dd==d and mm['commandId']==msg['commandId'] and mm['attemptNo']==1),None));d.state['workStatus']='IDLE';feed(row,d,retry,result,reason);return retry
def finish(row,max_steps=6):
 for _ in range(max_steps):
  status=q.op(f'/tasks/{row["taskId"]}')['status']
  if status in ['COMPLETED','FAILED','PENDING_MANUAL','MANUAL_TERMINATED']:break
  d,msg=accept(row);feed(row,d,msg)
 return obs(row)
def reset():
 for d in q.devices:d.paused=False;d.delivery_failures=set()
 q.reset()
def prefix(row):
 d,msg=accept(row);feed(row,d,msg);obs(row,'prefix');return accept(row)
