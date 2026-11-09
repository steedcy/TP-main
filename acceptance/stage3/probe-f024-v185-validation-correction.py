r=next(r for r in q.ev['cases'] if r['name']=='six-actions-rejected')
r['probeCorrection']={'originalChecks':copy.deepcopy(r['checks']),'originalResult':r['result'],'reason':'Six-step count gate rejects before persisting a plan version; actual PLAN_VALIDATED ERR_STEP_LIMIT_EXCEEDED event and zero commands are the rejection evidence'}
r['checks']['validationFail']=any(e.get('reasonCode')=='ERR_STEP_LIMIT_EXCEEDED' for e in r['after']['events']);r['result']='P' if all(r['checks'].values()) else 'F';q.save();result={'correctedSameObservation':r['taskId']}
