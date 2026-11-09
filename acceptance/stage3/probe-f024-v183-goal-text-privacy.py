marker='F183_GOAL_TEXT_PRIVACY';q.config(marker)
body={'taskGoal':marker+' 超规行李处置; passengerName=FICTIONAL_F183_GOAL_TEXT_CANARY','taskFamily':'OVERSIZE_BAGGAGE_HANDLING','sceneParams':{'baggageLocation':'F2_TEST_SERVICE','tempBusinessId':'F183-GOAL-TEXT','targetLocation':'F2_TEST_GATE'}}
response=raw(q.op,'/tasks',body);tid=(response.get('body',{}).get('data') or {}).get('id')
if tid:q.tasks.append(tid)
r=q.record('goal-text-privacy',{'taskId':tid,'request':body,'response':response})
if tid:
 o=q.drive(r);r['after']=o;serialized=json.dumps(o,ensure_ascii=False);journal=(L/'f024-v183-model-requests.jsonl').read_text(encoding='utf8');modelRows=[json.loads(line) for line in journal.splitlines() if marker in line];r['modelRows']=modelRows;r['checks']={'noIdentityPersisted':'FICTIONAL_F183_GOAL_TEXT_CANARY' not in serialized,'noIdentitySentToModel':'FICTIONAL_F183_GOAL_TEXT_CANARY' not in json.dumps(modelRows,ensure_ascii=False)};r['result']='P' if all(r['checks'].values()) else 'F';q.save();q.terminate(tid)
# The stage0 controlled API criteria do not define a counter-code enumeration.
# Preserve the original exploratory failure; do not invent a product whitelist.
r=next(r for r in q.ev['cases'] if r['name']=='counter-unconfigured');r['explorationAdjudication']={'originalResult':r['result'],'originalChecks':copy.deepcopy(r['checks']),'decision':'Excluded from acceptance P/F totals','basis':'Stage0 requires optional counter and scene/constraint resolution but gives no configured counter enumeration. This probe guessed a whitelist from the name alone; valid/invalid String vs Object, missing/blank and explicit legal point are separately tested. No product criterion is changed.'};r['result']='OBS';q.save();result={'taskId':tid,'result':'recorded'}
