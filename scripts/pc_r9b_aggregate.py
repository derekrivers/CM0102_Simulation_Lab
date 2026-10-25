"""R9b bounded aggregate parser, kept separate from campaign orchestration."""
from collections import Counter
import os
from pathlib import Path

READS = {'read', 'pread', 'pread64', 'fread', 'fread_unlocked'}
ITEM_READS = {'fread', 'fread_unlocked'}
OPENS = {'open', 'open64', 'openat', 'openat64', 'fopen', 'fopen64'}
MAPS = {'mmap', 'mmap64'}
CAP = 16 * 1024**2
ROW_CAP = 2048
ABNORMAL_CAP = 1024
PATH_CAP = 1024
U64 = 2**64 - 1
POLICY = 'POLICY\tx86_64-tsync-single-task-no-clone-v1'


def number(text, signed=False):
    value = int(text)
    if str(value) != text or value < (-2**63 if signed else 0) or value > (2**63-1 if signed else U64):
        raise ValueError('invalid bounded integer')
    return value


def decode(text):
    if len(text) >= PATH_CAP*2 or len(text) % 2:
        raise ValueError('oversized/odd path')
    raw = bytes.fromhex(text)
    if raw.hex() != text or b'\0' in raw:
        raise ValueError('noncanonical path')
    return os.fsdecode(raw)


def parse_trace(path, members):
    if path.stat().st_size > CAP:
        raise ValueError('trace oversized')
    data = path.read_bytes()
    if not data.endswith(b'\n'):
        raise ValueError('unterminated output')
    lines = data.decode('ascii').splitlines()
    if len(lines) < 3 or lines[:2] != ['PCR9BFILE1', POLICY]:
        raise ValueError('missing observation policy')
    footer = lines[-1].split('\t')
    if len(footer) != 5 or footer[0] != 'PCR9BDONE':
        raise ValueError('missing completion footer')
    events, row_count, abnormal_count, errors = map(number, footer[1:])
    if errors or row_count > ROW_CAP or abnormal_count > ABNORMAL_CAP:
        raise ValueError('observer overflow/saturation/failure')
    rows, abnormal = [], []
    seen, opened, read, mapped = Counter(), set(), set(), set()
    failures = mismatch = outside = unresolved = symlinks = 0
    unique = set()
    for line in lines[2:-1]:
        f = line.split('\t')
        if f[0] == 'R':
            if abnormal or len(f) != 18:
                raise ValueError('malformed aggregate row/order')
            index = number(f[1])
            op = f[2]
            ok, error, known, dev, ino = map(number, f[3:8])
            size = number(f[8], signed=True)
            calls, positive, requested, lower, items, nested, short = map(number, f[9:16])
            target, supplied = map(decode, f[16:18])
            if (index != len(rows) or op not in READS | OPENS | MAPS or ok not in (0, 1)
                    or known not in (0, 1) or error > 4095 or (ok and error)
                    or calls == 0 or positive > calls or nested > calls or short > calls
                    or lower > requested or (positive == 0) != (lower == 0)
                    or (op not in ITEM_READS and (items or short))
                    or (op in OPENS and (positive or requested or lower))
                    or (op in MAPS and (positive or lower))
                    or (known and not target)):
                raise ValueError('inconsistent aggregate counters')
            key = (op, ok, error, known, dev, ino, size, target, supplied)
            if key in unique:
                raise ValueError('duplicate aggregate key')
            unique.add(key)
            member = members.get(target) if known else None
            matched = bool(member and (dev, ino, size) ==
                           (member['dev'], member['ino'], member['bytes']))
            mismatch += calls if member and not matched else 0
            outside += calls if known and not member else 0
            unresolved += calls if (ok or lower) and not known and op not in MAPS else 0
            failures += calls if not ok else 0
            if supplied and Path(supplied).is_absolute():
                p = Path(supplied)
                symlinks += calls if any(q.is_symlink() for q in (p, *p.parents)) else 0
            if matched:
                if op in OPENS and ok:
                    opened.add(target)
                if op in READS and lower > 0:
                    read.add(target)
                if op in MAPS and ok:
                    mapped.add(target)
            seen[op] += calls
            rows.append({'operation': op, 'success': bool(ok), 'sampled_failure_errno': error,
                'identity_known': bool(known), 'dev': dev, 'ino': ino, 'bytes': size,
                'resolved_target': target, 'supplied_path': supplied,
                'manifest_identity_matched': matched, 'calls': calls,
                'positive_results': positive, 'requested_api_bytes': requested,
                'delivered_api_bytes_lower_bound': lower, 'complete_fread_items': items,
                'nested_calls': nested, 'short_multi_byte_fread_calls': short})
        elif f[0] == 'A':
            if len(f) != 9:
                raise ValueError('malformed abnormal detail')
            sequence, index = map(number, f[1:3])
            fd = number(f[3], signed=True)
            requested, lower, sampled_errno = map(number, f[4:7])
            target, supplied = map(decode, f[7:9])
            if (index >= len(rows) or sequence == 0 or sequence > events
                    or (abnormal and sequence <= abnormal[-1]['sequence'])
                    or lower > requested or sampled_errno > 4095
                    or target != rows[index]['resolved_target']
                    or supplied != rows[index]['supplied_path']):
                raise ValueError('invalid abnormal identity/sequence')
            abnormal.append({'sequence': sequence, 'row': index, 'fd': fd,
                'requested_api_bytes': requested, 'delivered_api_bytes_lower_bound': lower,
                'sampled_errno': sampled_errno, 'target': target, 'supplied_path': supplied})
        else:
            raise ValueError('unknown trace record')
    if (row_count != len(rows) or abnormal_count != len(abnormal)
            or events != sum(seen.values()) or events > U64):
        raise ValueError('footer/event accounting mismatch')
    # All failed calls must have individual detail; successful nonmanifest calls
    # may include expected private outputs, devices, and loader/runtime metadata.
    per_row = Counter(a['row'] for a in abnormal)
    root = os.path.commonpath(list(members)) if members else ''
    for i, row in enumerate(rows):
        target = row['resolved_target']
        outside_root = row['identity_known'] and not target.startswith(root+'/')
        if outside_root and per_row[i] != row['calls']:
            raise ValueError('lost outside-root detail')
    if any(per_row[i] > row['calls'] or (not row['success'] and per_row[i] != row['calls'])
           for i, row in enumerate(rows)):
        raise ValueError('lost/duplicate abnormal detail')
    if mismatch or unresolved:
        raise ValueError('required identity unresolved or mismatched')
    return {'record_count': events, 'aggregate_rows': len(rows),
        'abnormal_event_count': len(abnormal), 'operations': dict(sorted(seen.items())),
        'successful_open_manifest_files': len(opened), 'positive_read_manifest_files': len(read),
        'mapped_manifest_files': len(mapped), 'failed_operations': failures,
        'identity_mismatches': mismatch, 'outside_manifest_operations': outside,
        'unresolved_successes': unresolved, 'absolute_supplied_symlinks_at_analysis': symlinks,
        'observer_active_interval_complete': True, 'all_kernel_io_observed': False,
        'descriptor_policy': 'tsync-single-task-no-clone;async-signals-masked-per-api',
        'semantic_use_of_every_byte_proven': False, 'mapped_pages_read_proven': False,
        'api_totals_are_unique_bytes': False,
        'partial_fread_bytes_beyond_complete_items': 'unobserved',
        'read_manifest_identities': {k: members[k] for k in sorted(read)},
        'rows': rows, 'events': abnormal}