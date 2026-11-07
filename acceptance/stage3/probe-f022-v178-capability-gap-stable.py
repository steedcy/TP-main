"""Rerun definition no-mutation assertion with browser configuration writes paused.

The first full-table before/after comparison overlapped the independently authorized
UI definition creation. Retain that raw observation and compare the precise delta;
this fresh scope creates its fixture before the snapshot and runs without UI writes.
"""
import os, importlib.util, json
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL'] = 'capability-gap-stable'
path = Path(__file__).with_name('probe-f022-v178-round.py')
spec = importlib.util.spec_from_file_location('r', path)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
try:
    source = json.loads((path.parent/'evidence/SRS_F022-V1.178-http-20261107.json').read_text(encoding='utf-8'))
    assert source.get('endedAt'), 'Wait until primary probe and UI writes have ended'
    did = source['definitionIds'][0]
    definition = r.q.cfg(f'/task-definitions/{did}')
    r.q.definitions.append(did)
    r.q.definitionBody = dict(r.payload(definition), taskName=definition['taskName'])
    r.q.ev['reusedFixture'] = {'definitionId': did, 'source': 'primary current-version fixture, not historical P reuse', 'browserConfigurationWritesPaused': True}
    r.q.run('capability_gap', r.capability_gap)
finally:
    r.q.cleanup()
    r.q.ev['endedAt'] = r.m.now()
    r.q.save()
