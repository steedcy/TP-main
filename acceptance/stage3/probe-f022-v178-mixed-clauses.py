"""Natural-language mixed capability/location constraints with punctuation controls.

Expected behavior comes from F022.R07: preserve the meaning of two explicit clauses.
This is not an implementation-regex oracle. Same capability and destination, varying
only ordinary Chinese clause punctuation/order; no forbidden hardware command needed.
Run after primary adapters exit, without concurrent browser configuration writes.
"""
import os,importlib.util
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='mixed-clauses'
p=Path(__file__).with_name('probe-f022-v178-suite.py')
s=importlib.util.spec_from_file_location('suite',p);suite=importlib.util.module_from_spec(s);s.loader.exec_module(suite)
q=suite.q
try:
    q.setup()
    suite.scene=lambda target='F2_TEST_GATE':{'targetLocation':target}
    for args in [
        ('mixed-prohibit-location-allow-cap-semicolon','禁止前往F2_TEST_GATE；仅允许使用CAP_NAVIGATION能力。','F2_ZONE_A',True),
        ('mixed-prohibit-location-allow-cap-comma','禁止前往F2_TEST_GATE，仅允许使用CAP_NAVIGATION能力。','F2_ZONE_A',True),
        ('mixed-allow-cap-prohibit-location-comma','仅允许使用CAP_NAVIGATION能力，禁止前往F2_TEST_GATE。','F2_ZONE_A',True),
        ('mixed-allow-location-prohibit-other-cap-comma','仅允许前往F2_ZONE_A，禁止使用CAP_INFO_DISPLAY能力。','F2_ZONE_A',True),
    ]:
        q.run(args[0],lambda args=args:suite.description_case(*args))
finally:
    q.cleanup();q.ev['endedAt']=suite.m.now();q.save()
