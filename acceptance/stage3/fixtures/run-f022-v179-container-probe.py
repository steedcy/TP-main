"""Reproduce actual V1.179 packaged-class Spring registration without DB/Redis.
Run after mvn -o package -DskipTests. Set GPT_RUN_SUFFIX for a fresh evidence file.
Does not change production files or claim live HTTP/business acceptance.
"""
from pathlib import Path
from zipfile import ZipFile
import subprocess,os
R=Path(__file__).resolve().parents[3]
suffix='-'+os.environ['GPT_RUN_SUFFIX'] if os.environ.get('GPT_RUN_SUFFIX') else ''
target=R/f'acceptance/stage3/evidence/SRS_F022-V1.179-container-component-20261107{suffix}.json'
assert not target.exists(),'Preserve earlier evidence; select a fresh GPT_RUN_SUFFIX'
jar=R/'backend/target/airport-ai-app-1.0.0.jar';out=R/'.local-test/f022-v179-exploded';out.mkdir(exist_ok=True)
with ZipFile(jar) as z:
    for name in z.namelist():
        if name.endswith('/') or not name.startswith(('BOOT-INF/lib/','BOOT-INF/classes/')):continue
        path=(out/name).resolve();assert path.is_relative_to(out.resolve())
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
cp=str(out/'BOOT-INF/classes')+';'+str(out/'BOOT-INF/lib/*')
classes=R/'.local-test/f022-v179-probe-classes';classes.mkdir(exist_ok=True)
source=R/'acceptance/stage3/fixtures/F022V179ContainerProbe.java'
subprocess.run(['javac','-encoding','UTF-8','-cp',cp,'-d',str(classes),str(source)],check=True)
subprocess.run(['java','-cp',str(classes)+';'+cp,'F022V179ContainerProbe',str(target)],check=True)
