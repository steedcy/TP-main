"""Run a reviewed probe file in the already-owned localhost fixture process."""
import json,sys,urllib.request,urllib.error
from pathlib import Path
code=Path(sys.argv[1]).read_text(encoding='utf8')
req=urllib.request.Request('http://127.0.0.1:18135/exec',json.dumps({'code':code}).encode(),{'Content-Type':'application/json'},method='POST')
try:
 with urllib.request.urlopen(req,timeout=900) as r:print(r.read().decode())
except urllib.error.HTTPError as e:print(e.read().decode());raise
