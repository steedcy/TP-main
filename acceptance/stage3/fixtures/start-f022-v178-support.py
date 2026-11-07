import json,socket,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3]
for port in [18117,15179]:
 with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0,'owned port occupied'
cmds=[('model',18117,[sys.executable,str(R/'acceptance/stage3/fixtures/f022-v178-controlled-model.py')]),('vite',15179,['node','--max-old-space-size=384',str(R/'frontend/node_modules/vite/bin/vite.js'),'--config',str(R/'.local-test/vite-v142.mjs')])]
for name,port,cmd in cmds:
 log=(R/f'.local-test/{name}-v178.log').open('ab',buffering=0)
 p=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 (R/f'.local-test/{name}-v178-runtime.json').write_bytes(json.dumps({'pid':p.pid,'port':port,'tag':'V1.178'}).encode())
 print(name,p.pid)
