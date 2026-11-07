"""Observe browser-submitted task via actual HTTP/SQL, then disable definition.
Own supplementary fixture remains alive; browser task remains available until final cleanup.
"""
import os,importlib.util,json
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='ui-persistence'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f022-v175-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;m=r.m;SC=r.SC
row=r.case('browser-submission-persistence-disable');tid=int(m.sql(f"select max(id) from {SC}.tasks where task_goal='F175_SUPPORTED_FOUR_TYPES_COMPLETE browser actual submission'"));row['taskId']=tid;q.tasks.append(tid);before=r.capture(row,'beforeDisable');d=next(x for x in q.cfg('/task-definitions') if x['definitionCode']==before['task']['taskFamily']);q.cfg(f'/task-definitions/{d["id"]}/disable','POST');row['definitionId']=d['id'];after=r.capture(row,'afterDisable')
r.record(row,{'allFourBrowserValues':before['task']['sceneParams']=={'targetLocation':'F2_TEST_GATE','partyCount':2,'assist':True,'distance':2.5},'noDefaultSceneSubstitution':before['task']['taskGoal']=='F175_SUPPORTED_FOUR_TYPES_COMPLETE browser actual submission','persistedInSql':len(m.rows(f'select * from {SC}.tasks where id={tid}'))==1,'existingTaskUnchanged':before['task']==after['task'],'disabledActual':q.cfg(f'/task-definitions/{d["id"]}')['definitionStatus']=='DISABLED'})
q.ev['uiTaskId']=tid;q.ev['endedAt']=m.now();q.save();print('Browser task',tid)
