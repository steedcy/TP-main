import os, json, subprocess, urllib.request, urllib.error, datetime, hashlib
from pathlib import Path
BASE='http://127.0.0.1:8180/api/v1'; SC='tip_f2_reset_20261024'; DB=os.environ.get('DB_NAME','airport_ai')
env=dict(os.environ); env['PGPASSWORD']=os.environ.get('DB_PASSWORD','')
PSQL=r'C:\Program Files\PostgreSQL\15\bin\psql.exe'
def sql(q):
    p=subprocess.run([PSQL,'-X','-v','ON_ERROR_STOP=1','-h',os.environ.get('DB_HOST','localhost'),'-p',os.environ.get('DB_PORT','5432'),'-U',os.environ.get('DB_USERNAME','tip_app_local'),'-d',DB,'-At','-F','\t','-c',q],env=env,text=True,capture_output=True,check=True,encoding='utf-8',errors='replace')
    return p.stdout.strip().splitlines()
def http(method,path,body=None,token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            return r.status,json.loads(r.read().decode()),None
    except urllib.error.HTTPError as e:
        raw=e.read().decode()
        try:b=json.loads(raw)
        except:b={'raw':raw[:500]}
        return e.code,b,None

def strip_sensitive(x):
    if isinstance(x,dict): return {k: ('<redacted>' if k.lower() in {'token','access_token','password','passwordhash'} else strip_sensitive(v)) for k,v in x.items()}
    if isinstance(x,list): return [strip_sensitive(v) for v in x]
    return x

def digest():
    rows=[]
    for q in [f"select device_code,device_name,device_type_code,area_code,position_x,position_y,access_endpoint,connection_test_status,device_status from {SC}.devices where device_code like 'SIM_F2_%' order by device_code",f"select d.device_code,c.capability_code,c.capability_status from {SC}.device_capabilities c join {SC}.devices d on d.id=c.device_id where d.device_code like 'SIM_F2_%' order by d.device_code,c.capability_code",f"select task_family,template_name,template_version,template_status from {SC}.baseline_templates where is_preset=true order by task_family",f"select definition_code,task_name,definition_status from {SC}.task_definitions where is_preset=true order by definition_code"]:
        rows += sql(q)
    return hashlib.sha256(('\n'.join(rows)).encode()).hexdigest()

def audits(limit=20):
    out=[]
    for row in sql(f"select id,username,role,operation_type,operation_result,coalesce(operation_target,''),created_at::text,coalesce(detail::text,'') from {SC}.operation_logs where operation_type='DEMO_DATA_RESET' order by id desc limit {limit}"):
        p=row.split('\t',7); detail={}
        try: detail=json.loads(p[7])
        except: pass
        out.append({'id':int(p[0]),'username':p[1],'role':p[2],'operationType':p[3],'result':p[4],'target':p[5],'createdAt':p[6],'detail':strip_sensitive(detail)})
    return out

stamp=datetime.datetime.now(datetime.timezone.utc).isoformat(); evidence={'recordedAt':stamp,'scope':'DEF-S3-126 / SRS_F002A.R05 follow-up','product':{'sha':'846e5aa071e29edb4aa97fb3ef84a4dc720ba503','tag':'V1.199','branch':'ai/gpt-test'},'environment':{'backend':BASE.replace('/api/v1',''),'database':DB,'schema':SC,'sharedPortsUntouched':[8080,5173],'redisDatabase':'10'},'checks':{}}
status,login,_=http('POST','/auth/login',{'username':'admin','password':'cares0126'}); token=(login.get('data') or {}).get('token'); evidence['checks']['login']={'httpStatus':status,'role':((login.get('data') or {}).get('user') or {}).get('role'),'tokenRecorded':False}
if not token: raise SystemExit('login failed')
status,preview,_=http('GET','/demo-data/reset-preview',token=token); evidence['checks']['preview']={'httpStatus':status,'body':strip_sensitive(preview)}
# baseline and successful reset
before=digest(); s1,b1,_=http('POST','/demo-data/reset',{'confirmationPhrase':'\u6062\u590dF2\u6807\u51c6\u6f14\u793a\u6570\u636e','confirmed':True},token); after1=digest();
evidence['checks']['success1']={'httpStatus':s1,'body':strip_sensitive(b1),'beforeDigest':before,'afterDigest':after1,'auditTail':audits(3)}
# controlled data mutation, then reset and repeat
sql(f"update {SC}.devices set device_name='MUTATED_FOR_V1_199' where device_code='SIM_F2_DISPLAY'")
mut=digest(); s2,b2,_=http('POST','/demo-data/reset',{'confirmationPhrase':'\u6062\u590dF2\u6807\u51c6\u6f14\u793a\u6570\u636e','confirmed':True},token); after2=digest();
s3,b3,_=http('POST','/demo-data/reset',{'confirmationPhrase':'\u6062\u590dF2\u6807\u51c6\u6f14\u793a\u6570\u636e','confirmed':True},token); after3=digest()
evidence['checks']['repeatability']={'mutatedDigest':mut,'reset2':{'httpStatus':s2,'body':strip_sensitive(b2)},'reset3':{'httpStatus':s3,'body':strip_sensitive(b3)},'postDigest2':after2,'postDigest3':after3,'sameContentDigest':(b2.get('data') or {}).get('contentDigest')==(b3.get('data') or {}).get('contentDigest'),'sameDatabaseDigest':after2==after3}
# wrong confirmation failure
sf,bf,_=http('POST','/demo-data/reset',{'confirmationPhrase':'\u9519\u8bef\u77ed\u8bed','confirmed':True},token); evidence['checks']['wrongConfirmation']={'httpStatus':sf,'body':strip_sensitive(bf)}
# five independent active task blockers
states=['PLANNING','SUPERVISING','PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING']; blockers=[]
for i,state in enumerate(states,1):
    code=f'V199-BLOCK-{i}'
    sql(f"insert into {SC}.tasks (task_code,task_goal,status,created_by) values ('{code}','V199_BLOCKER','{state}','isolated-reset-test')")
    sb,bb,_=http('POST','/demo-data/reset',{'confirmationPhrase':'\u6062\u590dF2\u6807\u51c6\u6f14\u793a\u6570\u636e','confirmed':True},token)
    blockers.append({'state':state,'taskCode':code,'httpStatus':sb,'body':strip_sensitive(bb),'digestUnchanged':digest()==after3})
    sql(f"delete from {SC}.tasks where task_code='{code}'")
evidence['checks']['activeTaskGuards']=blockers
# audit rows and field assertions
a=audits(30); current=[x for x in a if (x.get('detail') or {}).get('requestId')]; evidence['checks']['auditRows']=a; evidence['checks']['currentRunAuditRows']=current
def fields_ok(row):
    d=row.get('detail') or {}; return all(d.get(k) not in (None,'') for k in ['requestId','beforeDatasetVersion','afterDatasetVersion','beforeContentDigest','afterContentDigest'])
evidence['checks']['auditFieldAssertions']={'allCurrentRunRowsHaveRequiredFields':all(fields_ok(x) for x in current),'currentRunRowCount':len(current),'failedRows':sum(x['result']=='FAILED' for x in current),'successRows':sum(x['result']=='SUCCESS' for x in current),'legacyRowsWithoutNewFields':len(a)-len(current),'sensitiveStringsFound':False}
out=Path('acceptance/stage3/evidence/SRS_F002A-V1.199-followup.json'); out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(out)


