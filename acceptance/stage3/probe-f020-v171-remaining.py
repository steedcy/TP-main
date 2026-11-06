"""Natural three-clarification counterexample and non-manual HTTP state gates.
State gate catalog uses explicitly SQL seeded rows; natural manual paths already
captured independently. All temporary catalog status changes restored exactly.
"""
import os,importlib.util,json
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='remaining';P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f020-v171-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m;SC=r.SC
def missing():
 q.family='SPECIAL_PASSENGER_SERVICE';row=r.new('natural-three-clarifications',{'goalOverride':{'infoComplete':False,'origin':None,'destination':None,'missingInfoQuestions':['Synthetic assistance type required','Synthetic origin required','Synthetic destination required']}})
 row['clarifications']=[]
 for _ in range(3):
  task=q.op(f"/tasks/{row['taskId']}");questions=task.get('missingInfoQuestions') or []
  row['clarifications'].append({'questions':questions,'response':r.raw(f"/tasks/{row['taskId']}/clarify",{'answers':{x:'Synthetic still unknown' for x in questions}})})
 o=r.capture(row,'afterThree');row['manualRejects']=[r.act(row,a,'F020 no missing information override') for a in ['SWITCH_TO_BASELINE','RETRY_PLANNING']];end=r.capture(row)
 r.record(row,{'threeRoundsSent':len(row['clarifications'])==3 and all(x['response']['http']==200 for x in row['clarifications']),'actualPendingManual':o['task']['status']=='PENDING_MANUAL','missingQuestionsRetained':len(o['task'].get('missingInfoQuestions') or [])>=3,'bothManualActionsBlocked':all(x['http']==400 for x in row['manualRejects']),'noPlanNoCommands':not end['plans'] and not end['commandRows'],'noDefaultInformationInjected':end['task'].get('sceneParams',{}).get('assistanceType') is None})
def gates():
 data=json.loads((P/'evidence/SRS_F020-V1.171-filter-catalog-stable2-20261106.json').read_text(encoding='utf8'));row={'name':'http-nonmanual-state-gates','fixtureLevel':'Synthetic catalog only, original final statuses restored','observations':[]};q.ev['cases'].append(row);checks={}
 for x in data['rows']:
  if x['status']=='PENDING_MANUAL':continue
  tid=x['id'];old=m.sql(f'select status from {SC}.tasks where id={tid}')
  try:
   m.sql(f"update {SC}.tasks set status={m.lit(x['status'])} where id={tid}");before=q.op(f'/tasks/{tid}');events=q.op(f'/tasks/{tid}/events');ret=[r.raw(f'/tasks/{tid}/manual-actions',{'action':a,'reason':'F020 invalid state control'}) for a in ['SWITCH_TO_BASELINE','RETRY_PLANNING','MARK_FAILED']];after=q.op(f'/tasks/{tid}');afterev=q.op(f'/tasks/{tid}/events');row['observations'].append({'state':x['status'],'id':tid,'responses':ret,'before':before,'after':after,'eventsBefore':events,'eventsAfter':afterev});checks[x['status']]=all(400<=z['http']<500 for z in ret) and before==after and events==afterev
  finally:m.sql(f"update {SC}.tasks set status={m.lit(old)} where id={tid}")
 r.record(row,checks)
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 q.run('natural-missing',missing);q.run('state-gates',gates)
finally:
 for rr in q.ev.get('rulesBefore',[]):
  if rr['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rr['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
