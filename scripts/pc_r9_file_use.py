#!/usr/bin/env python3
"""Bounded affirmative host-API file-use observations; all raw paths stay private."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import pc_r5_capture as r5

READS = {'read', 'pread', 'pread64', 'fread', 'fread_unlocked'}
OPENS = {'open', 'open64', 'openat', 'openat64', 'fopen', 'fopen64'}
MAPS = {'mmap', 'mmap64'}
OBSERVED = '2f471fb8c5b87f69cf51d5423e6ec4e92e95386ba33fda2b1827d01df7781451'
SAVE = '8e3a60abb32ae8864e32052de34aa2fea00f1709ef54531220e949eb0ba16f11'
CAPTURE = '014808018f7b20f60abaac5c71a0c509747259e309563650afe0d0cc79da6f40'


def inventory(game, manifest):
    r5.clean_identity(game, manifest)
    result = {}
    for line in manifest.read_text().splitlines():
        if line.startswith('#'):
            continue
        sha, count, rel = line.split('\t')
        p = game / rel
        st = p.stat()
        result[str(p.resolve())] = {'dev': st.st_dev, 'ino': st.st_ino,
            'bytes': int(count), 'sha256': sha}
    return result


def parse_trace(path, members):
    if path.stat().st_size > 16 * 1024**2:
        raise ValueError('trace oversized')
    lines = path.read_text(encoding='ascii').splitlines()
    if not lines or lines[0] != 'PCR9FILE1' or not lines[-1].startswith('PCR9DONE\t'):
        raise ValueError('incomplete trace')
    footer = [int(x) for x in lines[-1].split('\t')[1:]]
    if len(footer) != 3 or footer[1:] != [0, 0]:
        raise ValueError('observer dropped records or failed')
    seen, opened, read, mapped = Counter(), set(), set(), set()
    failures = identity_mismatch = unresolved = supplied_symlinks = outside = 0
    private = []
    for i, line in enumerate(lines[1:-1], 1):
        fields = line.split('\t')
        if len(fields) != 12:
            raise ValueError('malformed trace record')
        seq, op, ok, returned, requested, error, known, dev, ino, size, target, supplied = fields
        seq, ok, returned, requested, error, known, dev, ino, size = map(
            int, (seq, ok, returned, requested, error, known, dev, ino, size))
        if seq != i or op not in READS | OPENS | MAPS or ok not in (0, 1) or known not in (0, 1):
            raise ValueError('invalid trace sequence or operation')
        target = os.fsdecode(bytes.fromhex(target))
        supplied = os.fsdecode(bytes.fromhex(supplied))
        seen[op] += 1
        failures += not ok
        member = members.get(target) if known else None
        matched = bool(member and (dev, ino, size) ==
                       (member['dev'], member['ino'], member['bytes']))
        if member and not matched:
            identity_mismatch += 1
        if known and not member:
            outside += 1
        if ok and not known:
            unresolved += 1
        # Supplied relative paths cannot be resolved without call-time cwd/dirfd.
        # Retain them as unresolved rather than guessing their symlink identity.
        symlink = 'not-resolved'
        if supplied and Path(supplied).is_absolute():
            p = Path(supplied)
            symlink = any(x.is_symlink() for x in (p, *p.parents))
            supplied_symlinks += bool(symlink)
        if matched:
            if op in OPENS and ok:
                opened.add(target)
            if op in READS and returned > 0:
                read.add(target)
            if op in MAPS and ok:
                mapped.add(target)
        private.append({'sequence': seq, 'operation': op, 'success': bool(ok),
            'resolved_target': target, 'supplied_path': supplied,
            'manifest_identity_matched': matched, 'returned': returned,
            'requested': requested, 'errno': error,
            'supplied_symlink_at_analysis': symlink})
    if footer[0] != len(lines)-2:
        raise ValueError('footer record count mismatch')
    return {'record_count': footer[0], 'operations': dict(sorted(seen.items())),
        'successful_open_manifest_files': len(opened),
        'positive_read_manifest_files': len(read),
        'mapped_manifest_files': len(mapped),
        'failed_operations': failures, 'identity_mismatches': identity_mismatch,
        'outside_manifest_operations': outside, 'unresolved_successes': unresolved,
        'absolute_supplied_symlinks_at_analysis': supplied_symlinks,
        'observer_active_interval_complete': True,
        'all_kernel_io_observed': False,
        'semantic_use_of_every_byte_proven': False,
        'mapped_pages_read_proven': False,
        'read_manifest_identities': {k: members[k] for k in sorted(read)},
        'events': private}


def exact_noninterference(records, successful):
    endpoint = successful and len(records) == 4 and all(
        x.get('save', {}).get('sha256') == SAVE for x in records)
    captured = successful and len(records) == 4 and all(
        x.get('capture_complete') and x.get('capture', {}).get('sha256') == CAPTURE
        for x in records[1:])
    return endpoint, captured


def observer_source():
    return Path(__file__).with_name('pc_r9_file_observer.c')


def build(a):
    r5.newdir(a.output)
    a.admitted = True
    command = ['/usr/bin/cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
        '-fPIC', '-shared', str(observer_source()), '-o', str(a.output/'observer.so'),
        '-ldl', '-pthread']
    before = {'observer': r5.identity(observer_source()), 'driver': r5.identity(__file__),
        'compiler': r5.identity(Path('/usr/bin/cc').resolve()), 'command': command,
        'compiler_version': subprocess.check_output(['/usr/bin/cc', '--version'],
            text=True).splitlines()[0], 'sealed_unix_time_ns': time.time_ns()}
    r5.write(a.output/'build-before.json', before)
    subprocess.run(command, check=True, timeout=60)
    before['library'] = r5.identity(a.output/'observer.so')
    before['completed_unix_time_ns'] = time.time_ns()
    r5.write(a.output/'build-receipt.json', before)


def seal(a):
    expected = json.loads(Path(__file__).parents[1].joinpath(
        'docs/research/evidence/pc-r5-capture-v1.json').read_text())
    if r5.identity(a.observed/'build-receipt.json') != expected['build']['private_build_receipt']:
        raise ValueError('unsealed R5 build receipt')
    receipt = json.loads((a.observed/'build-receipt.json').read_text())
    if r5.identity(a.observed/'cm0102_observed')['sha256'] != OBSERVED:
        raise ValueError('wrong retained R5 derivative')
    if receipt['instrumented'] != r5.identity(a.observed/'cm0102_observed'):
        raise ValueError('R5 build receipt mismatch')
    if r5.identity(a.baseline)['sha256'] != r5.BASELINE:
        raise ValueError('wrong baseline')
    if r5.identity(a.source/'tests/smoke/smoke_run.py')['sha256'] != r5.SMOKE:
        raise ValueError('wrong pinned smoke')
    library = json.loads((a.library/'build-receipt.json').read_text())
    if library['library'] != r5.identity(a.library/'observer.so'):
        raise ValueError('library drift')
    if library['observer'] != r5.identity(observer_source()):
        raise ValueError('observer source drift')
    return {'source': r5.source_identity(a.source),
        'clean': r5.clean_identity(a.game, a.manifest),
        'manifest_members': inventory(a.game, a.manifest),
        'baseline': r5.identity(a.baseline),
        'derivative': r5.identity(a.observed/'cm0102_observed'),
        'r5_build_receipt': r5.identity(a.observed/'build-receipt.json'),
        'r5_executed_observer': receipt['observer'],
        'r9_build_receipt': r5.identity(a.library/'build-receipt.json'),
        'library': r5.identity(a.library/'observer.so'),
        'driver': r5.identity(__file__), 'r5_driver': r5.identity(r5.__file__),
        'python': r5.identity(Path(sys.executable).resolve()),
        'smoke': r5.identity(a.source/'tests/smoke/smoke_run.py'),
        'host_file_route': r5.identity(a.source/'src/recomp_rt/host/posix.c'),
        'libc': r5.identity(Path('/lib/x86_64-linux-gnu/libc.so.6').resolve()),
        'loader': r5.identity(Path('/lib64/ld-linux-x86-64.so.2').resolve())}


def run(a):
    initial = seal(a)
    old = json.loads((a.previous/'before.json').read_text())
    old_a = json.loads((a.previous/'enabled-a/command.json').read_text())
    if r5.identity(a.previous/'enabled-a/capture.bin')['sha256'] != CAPTURE:
        raise ValueError('retained capture mismatch')
    if r5.identity(a.previous/'baseline/user/samesave.sav')['sha256'] != SAVE:
        raise ValueError('retained save mismatch')
    script = old_a['environment']['RECOMP_SCRIPT']
    if hashlib.sha256(script.encode()).hexdigest() != old['script_sha256']:
        raise ValueError('retained smoke script mismatch')
    r5.newdir(a.output)
    a.admitted = True
    r5.write(a.output/'before.json', {'sealed_unix_time_ns': time.time_ns(),
        'identity': initial, 'script_sha256': old['script_sha256'],
        'retained_r5_before': r5.identity(a.previous/'before.json'),
        'retained_r5_receipt': r5.identity(a.previous/'receipt-private.json'),
        'limits': {'wall_seconds': 240, 'cpu_seconds': 300, 'address_space': 6*1024**3,
            'file_bytes': 64*1024**2, 'trace_bytes': 16*1024**2, 'each_stream': 1048576}})
    records = []
    for name in ['baseline', 'disabled', 'enabled-a', 'enabled-b']:
        work = a.output/name
        r5.newdir(work)
        for d in ['home', 'user']:
            r5.newdir(work/d)
        (work/'user/settings.txt').write_text('display = classic\nfaster_days = off\n')
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(work/'home'),
            'SDL_VIDEODRIVER': 'dummy', 'SDL_AUDIODRIVER': 'dummy', 'RECOMP_NO_BOX': '1',
            'RECOMP_USER_DIR': str(work/'user'), 'RECOMP_FIXED_CLOCK': '1',
            'RECOMP_SAVE_AFTER_DAYS': '14', 'RECOMP_IDLE_COUNT': '1', 'RECOMP_SCRIPT': script}
        program = a.baseline if name == 'baseline' else a.observed/'cm0102_observed'
        if name != 'baseline':
            env['PC_R5_CAPTURE'] = str(work/'capture.bin')
        if name.startswith('enabled'):
            env['LD_PRELOAD'] = str(a.library/'observer.so')
            env['PC_R9_TRACE'] = str(work/'trace.tsv')
            env['PC_R9_WAIT_FOR_STACK_REEXEC'] = '1'
        pre = seal(a)
        r5.write(work/'seal-before.json', {'sealed_unix_time_ns': time.time_ns(), 'identity': pre})
        if pre != initial:
            raise ValueError('pre-arm identity drift')
        with program.open('rb') as held:
            sha = hashlib.file_digest(held, 'sha256').hexdigest()
            if sha != (r5.BASELINE if name == 'baseline' else OBSERVED):
                raise ValueError('held executable mismatch')
            argv = ['/proc/self/fd/'+str(held.fileno()), '--game', str(a.game), '-seed', '1']
            r5.write(work/'command.json', {'argv': argv, 'environment': env, 'held_sha256': sha})
            code, streams, reason, elapsed = r5.bounded(argv, env, work)
        for filename, raw in zip(['stdout.log', 'stderr.log'], streams):
            (work/filename).write_bytes(raw)
        save = work/'user/samesave.sav'
        endpoint = code == 0 and reason is None and save.is_file() and re.search(
            rb'recomp: saved .* after 14 game days', streams[1]) is not None
        record = {'arm': name, 'exit_code': code, 'elapsed_seconds': elapsed,
            'execution_status': 'succeeded' if endpoint else 'failed',
            'reason': reason or ('completed-target' if endpoint else 'missing-endpoint'),
            'comparison_verdict': 'not-run', 'observation_completeness': 'disabled'}
        if save.is_file():
            record['save'] = r5.identity(save)
        if name != 'baseline':
            try:
                r5.parse_capture(work/'capture.bin')
                record['capture'] = r5.identity(work/'capture.bin')
                record['capture_complete'] = True
            except (ValueError, OSError):
                record['capture_complete'] = False
        if name.startswith('enabled'):
            try:
                summary = parse_trace(work/'trace.tsv', initial['manifest_members'])
                r5.write(work/'observation-private.json', summary)
                record['trace'] = r5.identity(work/'trace.tsv')
                record['observation'] = {k: v for k, v in summary.items()
                    if k not in ('events', 'read_manifest_identities')}
                record['observation_completeness'] = 'complete-at-observer-active-api-boundary'
            except (ValueError, OSError):
                record['observation_completeness'] = 'failed'
        post = seal(a)
        r5.write(work/'seal-after.json', {'sealed_unix_time_ns': time.time_ns(), 'identity': post})
        record['identities_stable'] = post == initial
        r5.write(work/'result.json', record)
        records.append(record)
        print(json.dumps({'arm': name, 'execution_status': record['execution_status'],
                          'elapsed_seconds': elapsed}), flush=True)
    stable = seal(a) == initial and all(x['identities_stable'] for x in records)
    successful = stable and all(x['execution_status'] == 'succeeded' for x in records)
    endpoint_equal, captured_equal = exact_noninterference(records, successful)
    observations = records[2:]
    complete = all(x['observation_completeness'] ==
        'complete-at-observer-active-api-boundary' for x in observations)
    positive = complete and all(x['observation']['positive_read_manifest_files'] > 0 and
        x['observation']['identity_mismatches'] == 0 for x in observations)
    report = {'schema_version': 1, 'execution_status': 'succeeded' if successful else 'failed',
        'observation_completeness': 'complete-at-observer-active-api-boundary' if complete else 'failed',
        'endpoint_noninterference': endpoint_equal, 'captured_ranges_noninterference': captured_equal,
        'positive_manifest_file_reads_observed': positive, 'all_kernel_io_observed': False,
        'semantic_use_of_every_byte_proven': False, 'mapped_pages_read_proven': False,
        'original_process_parity': 'not-claimed', 'comparison_verdict': 'not-run',
        'identities_stable': stable, 'results': records}
    r5.write(a.output/'after.json', {'sealed_unix_time_ns': time.time_ns(), 'identities_stable': stable})
    report['artifacts'] = {p.relative_to(a.output).as_posix(): r5.identity(p)
        for p in sorted(a.output.rglob('*')) if p.is_file()}
    r5.write(a.output/'receipt-private.json', report)
    public = {k: v for k, v in report.items() if k != 'artifacts'}
    public['private_receipt'] = r5.identity(a.output/'receipt-private.json')
    public['seals'] = {k: v for k, v in initial.items()
        if k not in ('manifest_members',)}
    r5.write(a.output/'receipt-public.json', public)
    return 0 if successful and endpoint_equal and captured_equal and positive else 1


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    b = commands.add_parser('build')
    r = commands.add_parser('run')
    for sub in (b, r):
        sub.add_argument('--output', type=Path, required=True)
    for flag in ('source', 'observed', 'baseline', 'game', 'manifest', 'library', 'previous'):
        r.add_argument('--'+flag, type=Path, required=True)
    a = parser.parse_args()
    for key, value in vars(a).items():
        if isinstance(value, Path) and not value.is_absolute():
            parser.error(key+' must be absolute')
    a.admitted = False
    try:
        if a.command == 'build':
            build(a)
            return 0
        return run(a)
    except Exception as error:
        if a.admitted:
            r5.write(a.output/'failed.json', {'execution_status': 'failed',
                'comparison_verdict': 'not-run', 'observation_completeness': 'failed',
                'error_type': type(error).__name__})
        print('pc-r9 failed: '+type(error).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
