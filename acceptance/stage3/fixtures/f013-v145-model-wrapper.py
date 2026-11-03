import importlib.util,json
from pathlib import Path
from http.server import ThreadingHTTPServer
r=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('model',r/'acceptance/stage3/fixtures/f013-v142-controlled-model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.JOURNAL=r/'.local-test/f013-v145-model-requests.jsonl';original=m.plan
def configurable(goal):
 path=r/'.local-test/f013-v145-model-cases.json'
 if path.exists():
  for name,steps in json.loads(path.read_text(encoding='utf-8')).items():
   if name in goal:return steps
 return original(goal)
m.plan=configurable
ThreadingHTTPServer(('127.0.0.1',18117),m.Handler).serve_forever()
