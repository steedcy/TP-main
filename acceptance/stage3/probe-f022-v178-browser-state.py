"""Corroborate actual browser submission, then disable its owned definition.
Primary probe must be waiting at UI sentinel; no concurrent configuration writer.
"""
import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3'
s=importlib.util.spec_from_file_location('m',D/'probe-f022-v178-base.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
fixture=json.loads((R/'.local-test/f022-v178-ui-ready.json').read_text(encoding='utf-8'))
cfg=m.l.API('配置管理员');op=m.l.API('运行操作员')
rows=m.rows(f"select * from {m.SC}.tasks where task_goal like 'F178_BROWSER%' order by id")
assert len(rows)==1
tid=rows[0]['id'];before=op(f'/tasks/{tid}')
assert before['sceneParams']=={'targetLocation':'F2_TEST_GATE','partyCount':2,'assist':True,'distance':2.5}
cfg(f"/task-definitions/{fixture['definitionId']}/disable",'POST')
evidence={'at':m.now(),'tag':'V1.178','productSha':m.SHA,'taskId':tid,'before':before,'persistedTask':rows,'disabledDefinition':cfg(f"/task-definitions/{fixture['definitionId']}"),'existingTaskAfter':op(f'/tasks/{tid}'),'enabledOptions':[d for d in op('/task-definitions') if d['definitionStatus']=='ENABLED']}
evidence['checks']={'exactTypedPersistence':True,'disabledNotSelectable':not any(d['id']==fixture['definitionId'] for d in evidence['enabledOptions']),'existingTaskRetained':evidence['existingTaskAfter']['id']==tid}
p=D/'evidence/SRS_F022-V1.178-browser-persistence-disable-20261107.json';assert not p.exists();p.write_bytes(json.dumps(evidence,ensure_ascii=False,indent=2).encode('utf-8'))
print('Browser task persisted and definition disabled',tid)
