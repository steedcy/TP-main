# Correct the probe's reasonCode/eventType confusion using the same raw observation;
# do not repeat successful business execution or erase the original diagnostic.
for r in q.ev['cases']:
 if r['name'].startswith('goal-') and 'closedLoopEvent' in r.get('checks',{}):
  r['probeCorrection']={'originalChecks':copy.deepcopy(r['checks']),'originalResult':r['result'],'reason':'OVERSIZE_HANDLING_CLOSED_LOOP is reasonCode of TASK_COMPLETED, not eventType; raw actual event already present'}
  r['checks']['closedLoopEvent']=any(e['eventType']=='TASK_COMPLETED' and e.get('reasonCode')=='OVERSIZE_HANDLING_CLOSED_LOOP' for e in r['after']['events']);r['result']='P' if all(r['checks'].values()) else 'F'
q.save();result={'cases':[(r['name'],r.get('taskId'),r.get('result')) for r in q.ev['cases']]}
