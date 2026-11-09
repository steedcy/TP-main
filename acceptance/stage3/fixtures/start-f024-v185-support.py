import subprocess,sys,json,socket
from pathlib import Path
R=Path(__file__).resolve().parents[3]
for port in [18117,15179,18132,18133,18134,18135,18136,18137]:
 with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0,port
p=subprocess.Popen([sys.executable,str(R/'acceptance/stage3/probe-f024-v185.py')],cwd=R,stdout=(R/'.local-test/f024-v185-runtime.log').open('ab',buffering=0),stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
(R/'.local-test/f024-v185-support-pid.json').write_text(json.dumps({'pid':p.pid,'script':'probe-f024-v185.py','ports':[18117,15179,18132,18133,18134,18135,18136,18137]}))
print('supportPid',p.pid)
