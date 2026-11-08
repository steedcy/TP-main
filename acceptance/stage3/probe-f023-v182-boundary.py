"""Current HTTP authorization/coordinate boundary checks in GPT-owned instance."""
import importlib.util,json,copy,urllib.request,urllib.error
from pathlib import Path
p=Path(__file__).with_name('probe-f023-v182-runtime.py')
s=importlib.util.spec_from_file_location('runtime182',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
cfg=m.b.l.API('配置管理员');code='G180_F023_0'
fields=['deviceName','areaCode','positionX','positionY','accessEndpoint','statusReportInterval','remark']
before={k:cfg('/devices/'+code).get(k) for k in fields};invalid=[]
for field in ['positionX','positionY']:
 for mode in ['null','missing']:
  body=copy.deepcopy(before)
  if mode=='null':body[field]=None
  else:body.pop(field)
  invalid.append({'field':field,'mode':mode,'response':m.raw(cfg,'/devices/'+code,body,'PUT')})
after={k:cfg('/devices/'+code).get(k) for k in fields};authorization=[]
for role in ['配置管理员','运行操作员','系统管理员']:
 ret=m.raw(m.b.l.API(role),'/situation/snapshot')
 authorization.append({'role':role,'http':ret['http'],'businessCode':ret['body'].get('code'),'count':len(ret['body']['data']['agents'])})
try:
 with urllib.request.urlopen('http://127.0.0.1:18129/api/v1/situation/snapshot') as r:unauth=r.status
except urllib.error.HTTPError as ex:unauth=ex.code
columns=m.rows(f"select column_name,is_nullable from information_schema.columns where table_schema={m.lit(m.SC)} and table_name='devices' and column_name in ('position_x','position_y') order by column_name")
checks={'all400':all(x['response']['http']==400 and x['response']['body']['code']==3001 for x in invalid),'noConfigMutation':before==after,'threeRoles200':all(x['http']==200 and x['businessCode']==200 for x in authorization),'noSession401':unauth==401,'bothNotNull':len(columns)==2 and all(x['is_nullable']=='NO' for x in columns)}
m.save('api-boundary-auth',{'at':m.now(),'tag':'V1.182','productSha':m.SHA,'invalid':invalid,'authorization':authorization,'unauthenticated':unauth,'columns':columns,'before':before,'after':after,'checks':checks})
print(checks);assert all(checks.values())
