"""Publish a new qualified four-channel baseline by a real successful protocol trial.
No direct DB fabrication of eligibility. Original enabled templates are preserved.
"""
steps=q.steps();fields={};tmpl=[];inputs={}
for s in steps:
 mappings=[]
 for key,value in s['inputParams'].items():
  if key in ['targetX','targetY']:continue
  src=key;inputs[src]=value
  schema=next((p for p in q.caps[s['capabilityType']]['inputParams'] if p['name']==key),{})
  fields[src]={'name':src,'type':schema.get('type','String'),'required':True,'defaultValue':str(value).lower() if isinstance(value,bool) else str(value)}
  mappings.append({'target':key,'source':'TEMPLATE_INPUT.'+src})
 tmpl.append({'capabilityType':s['capabilityType'],'paramMapping':mappings,'stepTimeout':180,'completionCondition':s['completionCondition']})
body={'templateName':'F184 qualified baggage '+str(time.time_ns()),'templateIntent':'OVERSIZE_BAGGAGE_HANDLING','inputParams':list(fields.values()),'steps':tmpl}
t=q.cfg('/baseline-templates','POST',body);q.templates.append(t['id']);q.save()
agents=[q.devices[1],q.devices[1],q.devices[2],q.devices[0]]
ret=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':inputs,'simulatedDevices':[{'stepSeq':i+1,'agentId':d.agent} for i,d in enumerate(agents)]})
r=q.record('baseline-four-channel-real-trial',{'taskId':ret['taskId'],'templateId':t['id'],'request':body,'response':ret});q.tasks.append(r['taskId']);q.save();o=q.drive(r);trial=q.cfg(f"/baseline-templates/{t['id']}/dry-runs/{r['taskId']}");r['trial']=trial;r['checks']={'completed':o['task']['status']=='COMPLETED','qualified':trial['result']=='SUCCESS'};r['result']='P' if all(r['checks'].values()) else 'F';q.save()
if r['result']=='P':
 q.cfg(f"/baseline-templates/{t['id']}/enable",'POST')
 for name,mode in [('high-risk-qualified-baseline',{'confidence':.79,'diverse':True}),('model-unavailable-qualified-baseline',{'planHttpStatus':503})]:
  r=q.submit(name,scene=inputs,**mode);r['before']=q.observe(r['taskId']);o=q.drive(r);plans=o['plans'];checks={'completed':o['task']['status']=='COMPLETED','qualifiedBaselineUsed':any(p['source']=='BASELINE_TEMPLATE' and p.get('frozenAt') for p in plans),'noUnvalidatedExecute':all(p['structureCheckResult']=='PASS' and p['capabilityCheckResult']=='PASS' and p['constraintCheckResult']=='PASS' for p in plans if p.get('frozenAt'))}
  if 'high-risk' in name:checks['highRiskObserved']=any(p.get('riskLevel')=='HIGH' for p in plans)
  r['checks']=checks;r['result']='P' if all(checks.values()) else 'F';q.save();q.terminate(r['taskId'])
 q.cfg(f"/baseline-templates/{t['id']}/disable",'POST')
result={'state':q.state(),'template':t['id']}
