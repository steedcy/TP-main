"""Independent F014 HTTP/persistence probe. Uses only the existing GPT schema."""
import importlib.util,json,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=mod('prior',ROOT/'acceptance/stage3/probe-f013-v149.py')
l=base.l;sql=base.sql;SC=base.SC
_paths={}
def save(name,obj):
 if name not in _paths:
  p=ROOT/'acceptance/stage3/evidence'/f'SRS_F014-V1.150-{name}-20261104.json'
  if p.exists():p=p.with_stem(p.stem+'-'+datetime.now().strftime('%H%M%S%f'))
  _paths[name]=p
 p=_paths[name]
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def metadata():return {'version':'V1.150','codeSha':'69b841fbc10afd1c4c1f944cc0cd5a647bed66f7','observedAt':datetime.now().astimezone().isoformat(),'schema':SC}
def raw(api,path,body,method='POST'):
 req=urllib.request.Request(l.BASE+path,json.dumps(body).encode(),{'Content-Type':'application/json','Authorization':'Bearer '+api.token},method=method)
 try:
  with urllib.request.urlopen(req,timeout=95) as r:return {'http':r.status,'body':json.load(r)}
 except urllib.error.HTTPError as e:return {'http':e.code,'body':json.load(e)}
def observe(api,tid):return base.observe(api,tid)
def step(cap='CAP_NAVIGATION',seq=1,params=None):return {'stepSeq':seq,'stepGoal':'Synthetic passenger service','capabilityType':cap,'inputParams':params or {'targetLocation':'F2_TEST_GATE'},'precondition':'device online','completionCondition':'routeGenerated=true','failureHandling':'manual handling','stepTimeout':60}
if __name__=='__main__':
 cfg=l.API('配置管理员');op=l.API('运行操作员');ev=metadata();ev['before']=cfg('/risk-rules');ev['invalid']=[]
 count=lambda:sql(f'select count(*) from {SC}.risk_rules')
 ev['countBefore']=count()
 code='GPT_F014_150_API'
 if any(x['ruleCode']==code for x in ev['before']):code+='_'+datetime.now().strftime('%H%M%S%f')
 valid={'ruleCode':code,'ruleContent':'Synthetic F014 validation fixture','enabled':False}
 inputs=[{},dict(valid,ruleCode=''),dict(valid,ruleCode=' '),dict(valid,ruleContent=''),dict(valid,ruleCode='x'*65),dict(valid,ruleContent='x'*1001),dict(valid,ruleCode='BAD CODE'),dict(valid,enabled=1),dict(valid,ruleContent=[])]
 for body in inputs:ev['invalid'].append({'request':body,'response':raw(cfg,'/risk-rules',body)})
 ev['countAfterInvalid']=count();ev['created']=raw(cfg,'/risk-rules',valid);ev['duplicate']=raw(cfg,'/risk-rules',valid)
 ev['afterCreate']=cfg('/risk-rules');ev['noop']=raw(cfg,f'/risk-rules/{code}/update',{'enabled':False})
 ev['update']=raw(cfg,f'/risk-rules/{code}/update',{'ruleContent':valid['ruleContent']+' revised','enabled':True})
 ev['disable']=raw(cfg,f'/risk-rules/{code}/update',{'enabled':False})
 ev['unauthorized']=raw(op,'/risk-rules',{})
 ev['audit']=sql(f"select operation_type,operation_target,operation_result,detail::text from {SC}.operation_logs where operation_type='RISK_RULE_CHANGE' and operation_target='{code}' order by id")
 ev['after']=cfg('/risk-rules')
 ev['checks']={'invalidAll400':all(x['response']['http']==400 for x in ev['invalid']),'noInvalidData':ev['countBefore']==ev['countAfterInvalid'],'create200':ev['created']['http']==200,'duplicate409':ev['duplicate']['http']==409,'unauthorized403':ev['unauthorized']['http']==403,'noopSameVersion':ev['noop']['body']['data']['ruleVersion']==ev['created']['body']['data']['ruleVersion'],'editAndToggleVersioned':ev['disable']['body']['data']['ruleVersion']=='V1.2'}
 save('rule-crud',ev);print(ev['checks'])
