"""Create round-specific support scripts from reviewed owned fixtures; no product edits."""
from pathlib import Path
R=Path(__file__).resolve().parents[3]
F=R/'acceptance/stage3/fixtures'
for src,dst in [('start-f022-v179-jar.py','start-f024-v183-jar.py'),('f022-v179-controlled-model.py','f024-v183-controlled-model.py')]:
 s=(F/src).read_text(encoding='utf8').replace('f022-v179','f024-v183').replace('F022_V179','F024_V183').replace('V1.179','V1.183').replace('v179','v183')
 (F/dst).write_text(s,encoding='utf8')
