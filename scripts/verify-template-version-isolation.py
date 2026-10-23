"""Verify that a trial for an old version cannot authorize the edited template."""
import importlib.util,pathlib,time
p=pathlib.Path(__file__).with_name('local-test-environment.py');s=importlib.util.spec_from_file_location('localenv',p);e=importlib.util.module_from_spec(s);s.loader.exec_module(e)
api=e.API();fixture=e.load(e.FIXTURES/'baselines.json')[2]
template=next(t for t in api('/baseline-templates') if t['isPreset'] and t['templateIntent']==fixture['taskFamily'])
path='/baseline-templates/'+str(template['id']);body={k:fixture[k] for k in ['inputParams','steps']}
agents={a['deviceCode']:a['agentId'] for a in api('/device-agents?page=1&size=100')['content']}
proof={'recordedAt':e.stamp(),'scope':'PREPARATION_SMOKE_ONLY'}
try:
    first=api(path,'PUT',body);e.control('SIM_F2_FLIGHT','delay:6000')
    result=api(path+'/dry-run','POST',{'inputParams':{p['name']:p['defaultValue'] for p in fixture['inputParams']},
        'simulatedDevices':[{'stepSeq':i+1,'agentId':agents[c]} for i,c in enumerate(fixture['devices'])]})
    edited=api(path,'PUT',body)
    assert first['templateVersion']!=edited['templateVersion']
    deadline=time.monotonic()+30
    while result['result']=='RUNNING' and time.monotonic()<deadline:
        time.sleep(1);result=api(path+'/dry-runs/'+str(result['taskId']))
    assert result['result']=='SUCCESS',result
    current=api(path);assert current['templateStatus']=='DRAFT'
    try:api(path+'/enable','POST')
    except RuntimeError as ex:assert '400' in str(ex);blocked=True
    else:raise AssertionError('Edited draft was enabled using an old version trial')
    proof.update(result='PASS',trialVersion=first['templateVersion'],editedVersion=edited['templateVersion'],oldTrial=result,
        editedStatus=current['templateStatus'],enableBlocked=blocked)
finally:
    e.control('SIM_F2_FLIGHT','delay:1000')
    restored=api(path,'PUT',body);trial=e.run_baseline(api,restored,fixture,agents)
    assert trial['result']=='SUCCESS',trial
    api(path+'/enable','POST');proof['restoredVersion']=restored['templateVersion'];proof['restoredTrial']=trial
    e.save(e.EVIDENCE/'20261022-template-version-isolation.json',proof)
print('Template version isolation:',proof.get('result'),'; restored and enabled',proof['restoredVersion'])
