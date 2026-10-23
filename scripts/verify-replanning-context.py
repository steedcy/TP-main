"""Controlled end-to-end replan checks, with two completed steps and quota three.
Run only while backend is explicitly using the local fault model profile.
"""
import importlib.util,pathlib,time,json
p=pathlib.Path(__file__).with_name('local-test-environment.py');s=importlib.util.spec_from_file_location('localenv',p);e=importlib.util.module_from_spec(s);s.loader.exec_module(e)
admin=e.API();operator=e.API('运行操作员');control=e.LOCAL/'planning-fault.json'
def step(seq,cap,params,condition):return {'stepSeq':seq,'stepGoal':'执行虚构航班变更通知','capabilityType':cap,'inputParams':params,
    'precondition':'前序步骤完成且设备在线空闲','completionCondition':condition,'failureHandling':'先恢复，再进行一次局部重新规划','stepTimeout':60}
initial=[step(1,'CAP_FLIGHT_UPDATE',{'flightNumber':'TEST1022','updateType':'GATE_CHANGE','updateContent':'虚构航班变更通知','displayDuration':60},'publishStatus=SUCCESS'),
 step(2,'CAP_INFO_DISPLAY',{'contentType':'TEXT','contentData':'虚构场景：后续服务通知准备','displayDuration':60},'displayStatus=SUCCESS'),
 step(3,'CAP_NOTIFICATION',{'notificationType':'BOTH','notificationContent':'虚构场景：请旅客查看服务通知','repeatCount':1},'notificationStatus=SUCCESS')]
replacement=[step(1,'CAP_INFO_DISPLAY',{'contentType':'TEXT','contentData':'虚构场景：现场通知渠道不可用，显示后续服务通知','displayDuration':60},'displayStatus=SUCCESS')]
out={'recordedAt':e.stamp(),'scope':'PREPARATION_SMOKE_ONLY','checks':[]}
for mode in ['success','failure','timeout']:
    goal=f'重规划准备验证-{mode}-{int(time.time())}：发布航班TEST1022变更并通过可用业务渠道完成后续服务通知，不要求实体运动。'
    proof={'mode':mode,'goal':goal};started=time.monotonic()
    try:
        e.save(control,{'goal':'success','planning':'success','replanning':mode,'delaySeconds':65,'initialPlanSteps':initial,'replanPlanSteps':replacement})
        for code in ['SIM_F2_DISPLAY','SIM_F2_FLIGHT']:e.control(code,'delay:6000')
        task=operator('/tasks','POST',{'taskGoal':goal,'taskFamily':'FLIGHT_CHANGE_RESPONSE','sceneParams':{'flightNumber':'TEST1022','targetLocation':'F2_TEST_GATE'}})
        for code in ['SIM_F2_ROBOT','SIM_F2_ROBOT_B']:admin('/devices/'+code+'/capabilities/CAP_NOTIFICATION/status','POST',{'status':'DISABLED'})
        deadline=time.monotonic()+110
        while task['status'] not in ['COMPLETED','PENDING_MANUAL','FAILED','MANUAL_TERMINATED'] and time.monotonic()<deadline:
            time.sleep(1);task=operator('/tasks/'+str(task['id']))
        requests=[json.loads(line) for line in (e.LOCAL/'planning-requests.jsonl').read_text(encoding='utf-8').splitlines()]
        replans=[row for row in requests if row['phase']=='replanning' and row['request']['taskGoal']==goal]
        assert len(replans)==1,('Expected one replan request',len(replans))
        request=replans[0]['request'];assert request['sceneParams']['flightNumber']=='TEST1022'
        assert request['remainingStepQuota']==3 and len(request['completedSteps'])==2
        assert all(s.get('outputParams') and s.get('originalCommandId') for s in request['completedSteps'])
        types={c['capabilityType'] for c in request['capabilityContext']}
        assert {'CAP_INFO_DISPLAY','CAP_FLIGHT_UPDATE','CAP_NAVIGATION','CAP_NOTIFICATION'}<=types
        assert request['constraints'] and task['replanUsed'] is True
        assert task['status']==('COMPLETED' if mode=='success' else 'PENDING_MANUAL'),task
        plans=operator(f"/tasks/{task['id']}/plan-versions")
        proof.update(result='PASS',task=task,request=request,plans=plans,steps=operator(f"/tasks/{task['id']}/step-assignments"),events=operator(f"/tasks/{task['id']}/events"))
        if mode=='success':
            current=next(p for p in plans if p['id']==task['currentPlanVersionId'])
            assert len(current['planSteps'])==3
        if mode=='timeout':assert time.monotonic()-started>=60
    except Exception as ex:proof.update(result='FAIL',error=str(ex))
    finally:
        for code in ['SIM_F2_ROBOT','SIM_F2_ROBOT_B']:
            cap=next(c for c in admin('/devices/'+code+'/capabilities') if c['capabilityCode']=='CAP_NOTIFICATION')
            if cap['capabilityStatus']=='DISABLED':admin('/devices/'+code+'/capabilities/CAP_NOTIFICATION/status','POST',{'status':'ENABLED'})
        for code in ['SIM_F2_DISPLAY','SIM_F2_FLIGHT']:e.control(code,'delay:1000')
        e.save(control,{'goal':'success','planning':'success','replanning':'success','delaySeconds':65})
    proof['elapsedSeconds']=round(time.monotonic()-started,3);out['checks'].append(proof)
    e.save(e.EVIDENCE/'20261022-replanning-context-smoke.json',out)
    print('Replanning '+mode+': '+proof['result'],flush=True)
if any(c['result']!='PASS' for c in out['checks']):raise SystemExit(1)
