"""Five-step valid boundary and independent hard validation rejection branches."""
valid=q.steps();five=copy.deepcopy(valid);fifth=copy.deepcopy(five[-1]);fifth['stepSeq']=5;five.append(fifth)
badstruct=copy.deepcopy(valid);badstruct[0].pop('precondition')
badcap=copy.deepcopy(valid);badcap[2]['capabilityType']='CAP_F185_FICTIONAL'
badmotion=copy.deepcopy(valid);badmotion[-1]['inputParams']['speed']=2
badchannel=copy.deepcopy(valid);badchannel[2]['capabilityType']='CAP_NAVIGATION';badchannel[2]['inputParams']=copy.deepcopy(valid[-1]['inputParams'])
six=copy.deepcopy(five);six.append({**copy.deepcopy(fifth),'stepSeq':6})
for name,steps,allowed in [('five-actions-boundary',five,True),('six-actions-rejected',six,False),('structure-missing-rejected',badstruct,False),('unknown-capability-rejected',badcap,False),('motion-safety-rejected',badmotion,False),('missing-display-rejected',badchannel,False)]:
 r=q.submit(name,steps=steps);o=q.drive(r) if allowed else q.observe(r['taskId']);checks={'httpRecorded':r['response']['http'] in [200,400]}
 if allowed:checks.update(completed=o['task']['status']=='COMPLETED',fiveExecuted=len([c for c in o['commandRows'] if c['command_type']=='EXECUTE_CAPABILITY'])==5)
 else:checks.update(noCommands=len(o['commandRows'])==0,notFrozen=all(not p.get('frozenAt') for p in o['plans']),validationFail=any(p[k]=='FAIL' for p in o['plans'] for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']))
 r['after']=o;r['checks']=checks;r['result']='P' if all(checks.values()) else 'F';q.save();q.terminate(r['taskId'])
result={'state':q.state()}
