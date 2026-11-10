import json, urllib.request, urllib.error, re, sys, datetime, subprocess
B='http://127.0.0.1:18130'
def get(path):
    try:
        with urllib.request.urlopen(B+path, timeout=10) as r: return r.status, r.headers.get('Content-Type'), r.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.headers.get('Content-Type'), e.read().decode()
for _ in range(3): get('/api/v1/users')  # generate http_server_requests samples (401/403 acceptable)
st, ct, body = get('/actuator/prometheus')
fams = ['jvm_memory_used_bytes','jvm_threads_live_threads','jvm_gc_pause_seconds_count','process_cpu_usage','process_uptime_seconds','system_cpu_usage','http_server_requests_seconds_count','http_server_requests_seconds_sum','hikaricp_connections_active','hikaricp_connections_max']
checks = {f: bool(re.search(r'^'+f+r'(\{| )', body, re.M)) for f in fams}
has_help = body.count('# HELP ') ; has_type = body.count('# TYPE ')
samples = {}
for f in fams:
    m = re.findall(r'^'+f+r'(?:\{[^}]*\})? ([0-9.eE+-]+|NaN)$', body, re.M)
    samples[f] = m[:3]
hs, _, hb = get('/actuator/health'); ms, _, mb = get('/actuator/metrics')
sha = subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()
res = {'sampledAt': datetime.datetime.now().astimezone().isoformat(), 'productTag':'V1.193','productSha':'d9ac610515168208ca5f78ef3a40f308f69d81d2','testBranchHead':sha,'baseUrl':B,'schema':'tip_gpt_nf018_v193_20261110',
 'prometheus':{'status':st,'contentType':ct,'bytes':len(body),'helpLines':has_help,'typeLines':has_type,'families':checks,'sampleValues':samples,
   'jvm':any(k.startswith('jvm') and v for k,v in checks.items()),'process':checks['process_cpu_usage'] and checks['process_uptime_seconds'],'http_server_requests':checks['http_server_requests_seconds_count']},
 'health':{'status':hs,'body':json.loads(hb).get('status') if hs==200 else hb[:100]},'metricsEndpoint':ms}
res['pass'] = st==200 and 'text/plain' in (ct or '') and all(checks.values()) and has_help>0 and has_type>0 and hs==200
out='acceptance/stage3/evidence/SRS_NF018-V1.193-prometheus-sample-20261110.json'
open(out,'w',encoding='utf-8').write(json.dumps(res,ensure_ascii=False,indent=2))
open('acceptance/stage3/evidence/SRS_NF018-V1.193-prometheus-raw-20261110.txt','w',encoding='utf-8').write(body)
print(json.dumps({k:res[k] for k in ('prometheus','health','metricsEndpoint','pass')},ensure_ascii=False,indent=1)[:2500])
