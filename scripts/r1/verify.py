#!/usr/bin/env python3
"""Execute the SAME Rust corpus natively and in raw WASM; never update goldens."""
import hashlib, json, pathlib, struct, subprocess, sys
root = pathlib.Path(__file__).resolve().parents[2]
out = pathlib.Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
def command(args, **kwargs):
    return subprocess.check_output(args, cwd=root, **kwargs)
for args in [
    ['cargo','fmt','-p','cm-rng','--check'],
    ['cargo','test','-p','cm-rng'],
    ['cargo','clippy','-p','cm-rng','--all-targets','--','-D','warnings'],
    ['cargo','build','-p','cm-rng','--example','corpus'],
    ['cargo','build','-p','cm-rng','--example','corpus','--target','wasm32-unknown-unknown'],
]:
    print(' '.join(args), flush=True)
    command(args)
native = command(['target/debug/examples/corpus'])
(out/'native.bin').write_bytes(native)
command(['node','scripts/r1/run_wasm.mjs','target/wasm32-unknown-unknown/debug/examples/corpus.wasm',str(out/'wasm.bin')])
wasm = (out/'wasm.bin').read_bytes()
assert native == wasm, 'native/WASM bytes diverge'
canonical_sha = hashlib.sha256(native).hexdigest()
assert canonical_sha == '1c8d5c5b3443386e18f2124f19dcebbde7999124e3b557b71f78507597ce0d16'
assert len(native) == 75952
counts = struct.unpack('<4I', native[-16:])
assert all(counts), 'negative control failed to discriminate'
receipt = {
    'schema_version': 1,
    'implementation_revision': command(['git','rev-parse','HEAD']).decode().strip(),
    'tools': {key: command(args).decode().strip() for key,args in {
        'rustc':['rustc','--version'], 'cargo':['cargo','--version'], 'node':['node','--version']}.items()},
    'oracle_revision':'9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345',
    'specimen_sha256':'0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86',
    'oracle_sha256':'b7794145182f3ee357c11bf53136351c4231b960ae8c69d560ab2732a2d2f692',
    'table_sha256':'befdec88f802582bba7450e418aaa39837036c8d038810158cfc7a998be1b3db',
    'execution_status':'passed', 'comparison_verdict':'exact_bytes_equal',
    'coverage': {'crt_steps':1024,'bounded_calls':2570,'sequential_checkpoints':512,'restored_continuations':511},
    'canonical_bytes':len(native), 'native_sha256':canonical_sha,'wasm_sha256':hashlib.sha256(wasm).hexdigest(),
    'negative_control_mismatches':dict(zip(['wrong_crt_multiplier','early_wrap','extra_crt_draw','zero_mutation'],counts)),
    'checks':['fmt','test','clippy -D warnings','native build','wasm build','native execution','actual WASM execution'],
    'scope':'Synthetic table and original-instruction corpus; no x87, OS seeding, original saves, actual table, game-process or whole-game claim',
}
(out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
