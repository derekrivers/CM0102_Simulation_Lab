"""Internal fixed LAB-005 adapter; execution approval belongs to the lab registry."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

# -I intentionally removes the script directory; import only these pinned siblings.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab005_decoder_a
import lab005_decoder_b

PINS = {'image.bin': 'ae11ce3ef6267ad55be6aa6387f676704b1bb8a6310507db6c5ccfe494d45c3a',
        'heap.bin': '30ee2baefad8f57f8760f30abc076586f2d13339bb1629f75346a5dcbc1357a0'}
SOURCE_FILES = ['scripts/lab005.py', 'scripts/lab005_decoder_a.py',
                'scripts/lab005_decoder_b.py', 'scripts/lab005_tests.py',
                'docs/research/LAB_005_V1.md']


class InputRejected(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(mutation=None):
    """Entirely synthetic known census: fifty members, one associated manager."""
    cb, sb, pb = 0x10000, 0x20000, 0x30000
    globals_ = [(address, value.to_bytes(4, 'little')) for address, value in (
        (0xae235c, 3), (0xae2350, 1), (0xae2364, 60), (0xae236c, 50),
        (0xae23b4, cb), (0xae23bc, sb), (0xae23c4, pb))]
    clubs, staff, players = bytearray(3*581), bytearray(60*110), bytearray(50*70)

    def put(data, offset, value):
        data[offset:offset+4] = value.to_bytes(4, 'little')

    for n in range(3):
        put(clubs, n*581, n)
    put(clubs, 0xcf, sb+59*110)
    for n in range(60):
        put(staff, n*110, n)
        put(staff, n*110+0x39, cb if n < 50 or n == 59 else cb+581)
        if n < 50:
            put(staff, n*110+0x61, pb+n*70)
            put(players, n*70, n)
            put(clubs, 0xd7+n*4, sb+n*110)
    if mutation == 'unaligned-link':
        put(clubs, 0xd7, sb+1)
    elif mutation == 'duplicate-slot':
        put(clubs, 0xd7+49*4, sb)
    elif mutation == 'wrong-id':
        put(players, 0, 123456)
    elif mutation == 'truncated-record':
        players = players[:-1]
    elif mutation == 'changed-backpointer':
        put(staff, 0x39, cb+581)
    elif mutation not in (None, 'omitted-slot'):
        raise ValueError('unknown-control')
    ranges = globals_+[(sb, bytes(staff)), (pb, bytes(players))]
    if mutation == 'omitted-slot':
        hole = 0xd7+49*4
        ranges.extend([(cb, bytes(clubs[:hole])), (cb+hole+4, bytes(clubs[hole+4:]))])
    else:
        ranges.append((cb, bytes(clubs)))
    return ranges


def known_ledger():
    """Explicit fixture oracle, never used to classify captured records."""
    ranges = dict(fixture())
    staff, slots, players = [], [], []
    for n in range(60):
        row = {'pointer': 0x20000+n*110, 'staff_index': n, 'staff_id': n,
               'club_pointer': 0x10000 if n < 50 or n == 59 else 0x10000+581,
               'player_pointer': 0x30000+n*70 if n < 50 else 0,
               'player_index': n if n < 50 else None, 'player_id': n if n < 50 else None,
               'staff_sha256': sha(ranges[0x20000][n*110:(n+1)*110]),
               'player_sha256': sha(ranges[0x30000][n*70:(n+1)*70]) if n < 50 else None,
               'flags': [] if n < 50 else ['null-player'] if n == 59 else ['foreign-club', 'null-player'],
               'primary': 'candidate' if n < 50 else 'null-player' if n == 59 else 'foreign-club'}
        staff.append(dict(row, associated=n < 50 or n == 59))
        if n < 50:
            slots.append(dict(row, slot=n, duplicate_staff=False, duplicate_player=False))
            players.append({'index': n, 'id': n, 'complete': True, 'id_matches': True,
                            'sha256': row['player_sha256']})
    return {'dimensions': {'clubs': 3, 'nations': 1, 'staff': 60, 'players': 50},
            'binding': 0x10000, 'slots': slots, 'staff': staff, 'players': players}


def controls():
    """Both real decoders must match explicit positive and mutation expectations."""
    results = []
    for label, decoder in (('a', lab005_decoder_a.decode), ('b', lab005_decoder_b.decode)):
        baseline = decoder(fixture())
        good = (baseline == known_ledger() and len(baseline['slots']) == 50 and len(baseline['staff']) == 60 and
                len(baseline['players']) == 50 and
                [row['staff_id'] for row in baseline['slots']] == list(range(50)) and
                all(row['primary'] == 'candidate' for row in baseline['slots']) and
                all(not row['duplicate_staff'] and not row['duplicate_player'] for row in baseline['slots']) and
                sum(row['associated'] is True for row in baseline['staff']) == 51 and
                sum(row['primary'] == 'candidate' for row in baseline['staff']) == 50 and
                baseline['staff'][59]['primary'] == 'null-player' and
                all(row['complete'] and row['id_matches'] for row in baseline['players']))
        results.append({'decoder': label, 'control': 'positive-known-census', 'passed': good})
        expected = {'unaligned-link': (0, 'unaligned-staff'),
                    'duplicate-slot': (49, 'candidate'), 'wrong-id': (0, 'wrong-player-id'),
                    'truncated-record': (49, 'missing-player'),
                    'changed-backpointer': (0, 'foreign-club'), 'omitted-slot': (49, 'missing-slot')}
        for mutation, (slot, primary) in expected.items():
            actual = decoder(fixture(mutation))
            passed = (actual != baseline and len(actual['slots']) == 50 and
                      len(actual['staff']) == 60 and actual['slots'][slot]['primary'] == primary)
            if mutation == 'duplicate-slot':
                passed = passed and actual['slots'][49]['duplicate_staff'] and actual['slots'][49]['duplicate_player']
                passed = passed and len({r['staff_id'] for r in actual['slots']}) == 49
            if mutation == 'omitted-slot':
                passed = passed and actual['slots'][49]['pointer'] is None
            if mutation == 'truncated-record':
                passed = passed and not actual['players'][49]['complete']
            results.append({'decoder': label, 'control': mutation, 'passed': bool(passed)})
    for mutation in (None, 'unaligned-link', 'duplicate-slot', 'wrong-id',
                     'truncated-record', 'changed-backpointer', 'omitted-slot'):
        results.append({'decoder': 'comparison', 'control': mutation or 'positive-known-census',
                        'passed': lab005_decoder_a.decode(fixture(mutation)) == lab005_decoder_b.decode(fixture(mutation))})
    return results


def summarize(parsed):
    slots, staff, players = parsed['slots'], parsed['staff'], parsed['players']
    listed = {(r['staff_index'], r['player_index']) for r in slots if r['primary'] == 'candidate'}
    inverse = {(r['staff_index'], r['player_index']) for r in staff if r['primary'] == 'candidate'}
    duplicate_candidates = sum(r['primary'] == 'candidate' and r['duplicate_staff'] for r in slots)
    missing = sum(any(flag.startswith('missing-') for flag in r['flags']) for r in slots+staff)
    missing += sum(not r['complete'] for r in players)
    counts = {'slots': len(slots), 'staff': len(staff), 'players': len(players),
              'slot_primary': dict(Counter(r['primary'] for r in slots)),
              'staff_primary': dict(Counter(r['primary'] for r in staff)),
              'slot_flags': dict(Counter(f for r in slots for f in r['flags'])),
              'staff_flags': dict(Counter(f for r in staff for f in r['flags'])),
              'associated': sum(r['associated'] is True for r in staff),
              'excluded_association': sum(r['associated'] is False for r in staff),
              'unknown_association': sum(r['associated'] is None for r in staff),
              'duplicate_staff_slots': sum(r['duplicate_staff'] for r in slots),
              'duplicate_player_slots': sum(r['duplicate_player'] for r in slots),
              'duplicate_candidate_slots': duplicate_candidates,
              'duplicate_staff_table_player_links': sum(n-1 for n in Counter(
                  r['player_pointer'] for r in staff if r['player_pointer'] not in (None, 0)).values()),
              'player_id_mismatch': sum(r['id_matches'] is False for r in players),
              'player_missing_records': sum(not r['complete'] for r in players),
              'listed_candidates': len(listed), 'inverse_candidates': len(inverse),
              'intersection': len(listed & inverse), 'list_only': len(listed-inverse),
              'inverse_only': len(inverse-listed), 'missing_observations': missing}
    unresolved_identity = counts['player_id_mismatch'] or counts['staff_flags'].get('wrong-staff-id', 0)
    return {'counts': counts, 'hashes': {'ledger': sha(canonical(parsed)),
            'slots': sha(canonical(slots)), 'staff': sha(canonical(staff)),
            'players': sha(canonical(players)), 'listed_set': sha(canonical(sorted(listed))),
            'inverse_set': sha(canonical(sorted(inverse)))},
            'hypothesis_conclusion': 'unresolved' if missing or unresolved_identity else
                ('supported' if listed == inverse and not duplicate_candidates else 'contradicted'),
            'observation_status': 'censored' if missing else 'completed',
            'hypothesis_reason': 'missing-extents' if missing else 'inconsistent-table-identities'
                if unresolved_identity else 'exact-structural-set-comparison'}


def exact_differences(left, right, path='$'):
    """No masks or tolerances. Private leaf differences retain both exact values."""
    if type(left) is not type(right):
        return [{'path': path, 'a': left, 'b': right}]
    if isinstance(left, dict):
        differences = []
        for key in sorted(left.keys() | right.keys()):
            if key not in left or key not in right:
                differences.append({'path': path+'.'+key, 'a_present': key in left,
                                    'b_present': key in right, 'a': left.get(key), 'b': right.get(key)})
            else:
                differences.extend(exact_differences(left[key], right[key], path+'.'+key))
        return differences
    if isinstance(left, list):
        if len(left) != len(right):
            return [{'path': path, 'a': left, 'b': right}]
        return [change for i, (a, b) in enumerate(zip(left, right))
                for change in exact_differences(a, b, f'{path}[{i}]')]
    return [] if left == right else [{'path': path, 'a': left, 'b': right}]


def write_private(path, value):
    with path.open('x', encoding='utf8') as stream:
        path.chmod(0o600)
        json.dump(value, stream, sort_keys=True, separators=(',', ':'), allow_nan=False)
        stream.write('\n')
    return sha(path.read_bytes())


def run(capture_path, attempt_path):
    """Read pinned inputs; write immutable private evidence; return sanitized outcome."""
    start, cpu = time.monotonic(), time.process_time()
    capture, attempt = Path(capture_path), Path(attempt_path)
    if attempt.is_symlink() or not attempt.is_dir():
        raise ValueError('regular-attempt-directory-required')
    private = attempt/'lab005-private'
    private.mkdir(mode=0o700)  # Exclusive: never replace any earlier attempt.
    outcome = {'execution_status': 'failed', 'comparison_verdict': 'inconclusive',
               'details': {'hypothesis_conclusion': 'unresolved', 'hypothesis_reason': 'not-evaluated',
                           'production_admission': 'none', 'accounting': [
                               {'decoder': name, 'planned_slots': 50, 'observed_slots': 0,
                                'declared_staff': None, 'observed_staff': 0,
                                'declared_players': None, 'observed_players': 0,
                                'observation_status': 'unstarted'} for name in ('a', 'b')]}}
    try:
        ranges = []
        for name, base, limit in (('image.bin', 0x400000, 12000000),
                                   ('heap.bin', 0x70000000, 120000000)):
            path = capture/name
            if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
                raise InputRejected('unsupported-input-object')
            with path.open('rb') as stream:
                raw = stream.read(limit+1)
            if len(raw) > limit or sha(raw) != PINS[name]:
                raise InputRejected('input-identity-mismatch')
            ranges.append((base, raw))
        control_results = controls()
        outcome['details']['controls_sha256'] = write_private(private/'controls.json', control_results)
        outcome['details']['controls_total'] = len(control_results)
        outcome['details']['controls_passed'] = sum(r['passed'] for r in control_results)
        if not all(r['passed'] for r in control_results):
            raise ValueError('nondiscriminating-control')
        decoded = []
        decode_errors = []
        for name, decoder in (('a', lab005_decoder_a.decode), ('b', lab005_decoder_b.decode)):
            accounting = next(r for r in outcome['details']['accounting'] if r['decoder'] == name)
            try:
                parsed = decoder(ranges)
            except Exception as error:
                write_private(private/f'decoder-{name}-error.json', {'type': type(error).__name__, 'message': str(error)})
                dimensions = getattr(error, 'dimensions', None) or {}
                accounting.update(declared_staff=dimensions.get('staff'),
                                  declared_players=dimensions.get('players'), observation_status='censored')
                decode_errors.append(name)
                continue
            accounting.update(declared_staff=parsed['dimensions']['staff'],
                              declared_players=parsed['dimensions']['players'],
                              observed_slots=len(parsed['slots']), observed_staff=len(parsed['staff']),
                              observed_players=len(parsed['players']), observation_status='completed')
            write_private(private/f'decoder-{name}.json', parsed)
            decoded.append(parsed)
        if decode_errors:
            raise ValueError('decoder-boundary-unavailable')
        differences = exact_differences(*decoded)
        outcome['details']['comparison_sha256'] = write_private(private/'comparison.json',
            {'equal': not differences, 'differences': differences})
        outcome['details']['decoders'] = [summarize(x) for x in decoded]
        outcome['details']['hypothesis_conclusion'] = ('unresolved' if differences else
            outcome['details']['decoders'][0]['hypothesis_conclusion'])
        outcome['details']['hypothesis_reason'] = ('parser-disagreement' if differences else
            outcome['details']['decoders'][0]['hypothesis_reason'])
        outcome['execution_status'] = 'succeeded'
        outcome['comparison_verdict'] = 'different' if differences else 'equal'
        if any(r['counts']['missing_observations'] for r in outcome['details']['decoders']):
            outcome['details']['hypothesis_conclusion'] = 'unresolved'
            outcome['details']['hypothesis_reason'] = 'missing-extents'
    except Exception as error:
        write_private(private/'failure.json', {'type': type(error).__name__, 'message': str(error)})
        # Exception messages can contain private paths or data. Only type is public.
        outcome['details']['failure_type'] = type(error).__name__
        if isinstance(error, InputRejected):
            outcome['execution_status'] = 'rejected'
            outcome['comparison_verdict'] = 'not-run'
            outcome['details']['hypothesis_reason'] = 'input-not-admitted'
    dispositions = Counter(row['observation_status'] for row in outcome['details']['accounting'])
    outcome['details']['decoder_counts'] = {'planned': 2, 'completed': dispositions['completed'],
        'failed': dispositions['censored'], 'unstarted': dispositions['unstarted']}
    outcome['details']['input_sha256'] = PINS
    root = Path(__file__).resolve().parent.parent
    outcome['details']['source_sha256'] = {name: sha((root/name).read_bytes()) for name in SOURCE_FILES}
    outcome['details']['wall_seconds'] = time.monotonic()-start
    outcome['details']['cpu_seconds'] = time.process_time()-cpu
    try:
        import resource
        outcome['details']['peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:
        outcome['details']['peak_rss_kib'] = None
    write_private(attempt/'lab005-result.json', outcome)
    return outcome


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('attempt', type=Path)
    args = parser.parse_args()
    result = run(args.capture, args.attempt)
    print(json.dumps({'execution_status': result['execution_status'],
                      'comparison_verdict': result['comparison_verdict']}))
    raise SystemExit(0 if result['execution_status'] == 'succeeded' else 1)
