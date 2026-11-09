"""Actual feedback failure/one retry/candidate switch/local replan matrix."""
for name,cap,n,mode in [('measure-retry-success','CAP_BAGGAGE_MEASURE',1,{}),('measure-candidate-success','CAP_BAGGAGE_MEASURE',2,{}),('guide-retry-success','CAP_NAVIGATION',1,{}),('guide-candidate-success','CAP_NAVIGATION',2,{}),('guide-replan-success','CAP_NAVIGATION',4,{'replanSteps':[{**q.steps()[-1],'stepSeq':1}]}),('guide-replan-failure','CAP_NAVIGATION',4,{'replanHttpStatus':503})]:
 r=q.submit(name,**mode);o=q.drive(r,failcap=cap,failures=n);ev=o['events'];replans=[e for e in ev if e['eventType']=='REPLANNING_TRIGGERED'];expectedManual=name.endswith('failure')
 checks={'feedback200':all(a['response']['http']==200 for a in r.get('actions',[])),'outcome':o['task']['status']==('PENDING_MANUAL' if expectedManual else 'COMPLETED'),'atMostOneReplan':len(replans)<=1,'retryObserved':any(e['eventType']=='STEP_RETRY_DISPATCHED' for e in ev)}
 if 'candidate' in name:checks['twoDistinctDevices']=len({a['deviceCode'] for a in r.get('actions',[]) if a['message']['commandType']=='EXECUTE_CAPABILITY' and a['message'].get('capabilityType')==cap})==2
 if 'replan' in name:checks.update(oneReplan=len(replans)==1,prefixResultsPreserved=all(any(a['stepSeq']==seq and a['stepStatus']=='COMPLETED' for a in o['assignments']) for seq in [1,2,3]),replanUsed=o['task'].get('replanUsed') is True)
 r['checks']=checks;r['result']='P' if all(checks.values()) else 'F';q.save();q.terminate(r['taskId'])
result={'state':q.state()}
