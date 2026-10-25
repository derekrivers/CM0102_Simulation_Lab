#!/usr/bin/env python3
"""Convert hash-pinned public synthetic oracle to compact LE input/expected records."""
import hashlib, json, pathlib, struct, sys
source = pathlib.Path(sys.argv[1])
raw = (source / 'x86-oracle.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'b7794145182f3ee357c11bf53136351c4231b960ae8c69d560ab2732a2d2f692'
assert hashlib.sha256((source/'random-table.bin').read_bytes()).hexdigest() == 'befdec88f802582bba7450e418aaa39837036c8d038810158cfc7a998be1b3db'
data = json.loads(raw)
words = [1024, 2570, len(data['sequential_cases'])]
for case in data['crt']:
    before = case['seed']
    for step in case['steps']:
        words.extend([before, step['value'], step['state']])
        before = step['state']
for case in data['bounded_cases'] + data['sequential_cases']:
    words.append(case['bound'])
    words.extend(case['initial'][key] for key in ['cursorIndex','offset','crtState'])
    words.append(case['value'])
    words.extend(case['final'][key] for key in ['cursorIndex','offset','crtState'])
output = pathlib.Path(__file__).resolve().parents[2]/'crates/cm-rng/fixtures/corpus.bin'
output.write_bytes(b''.join(struct.pack('<I', word & 0xffffffff) for word in words))
print(hashlib.sha256(output.read_bytes()).hexdigest())
