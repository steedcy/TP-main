"""Run from GPT worktree root with own retained task536 and fresh output paths. Explicit synthetic PENDING UI seed; always resolves only its inserted row. No business transition claim."""
import importlib.util,json,subprocess
from pathlib import Path
r=Path.cwd();s=importlib.util.spec_from_file_location('m',r/'acceptance/stage3/probe-f018-v164.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);op=m.l.API('运行操作员')
ev={'tag':'V1.164','productSha':m.SHA,'at':m.now(),'fixture':'Explicit synthetic PENDING row for UI filter/card linkage only; existing real failed optional-step PROCESSING records remain.'}
ev['seedId']=int(m.sql(f"insert into {m.SC}.task_exceptions(task_id,step_seq,exception_type,reason_code,exception_status,recovery_action,impact_conclusion) values (536,2,'CAPABILITY_GAP','SYNTHETIC_UI_CARD_PENDING','PENDING','UI fixture only','Synthetic card filter sample') returning id").splitlines()[0]);ev['databaseCount']=int(m.sql(f"select count(*) from {m.SC}.task_exceptions e join {m.SC}.tasks t on t.id=e.task_id where not t.is_dry_run and e.exception_status in ('PENDING','PROCESSING')"));ev['overview']=op('/dashboard/overview');ev['pendingCountApi']=op('/task-exceptions/pending-count')
try:
 p=subprocess.run(['node',str(r/'acceptance/stage3/retest-f018-v164-card-stable.cjs'),str(ev['databaseCount'])],cwd=r,capture_output=True,encoding='utf-8',timeout=120);ev['ui']={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr};print(ev['ui'])
finally:
 m.sql(f"update {m.SC}.task_exceptions set exception_status='RESOLVED',resolved_at=localtimestamp,resolved_by='GPT_UI_FIXTURE_CLEANUP' where id={ev['seedId']}");ev['afterOverview']=op('/dashboard/overview');(r/'acceptance/stage3/evidence/SRS_F018-V1.164-card-stable-fixture-20261105.json').write_bytes(json.dumps(ev,ensure_ascii=False,indent=2).encode('utf-8'))
