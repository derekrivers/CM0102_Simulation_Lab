#!/usr/bin/env python3
"""Compare actual Rust/WASM corpus against retained original effects, no emulator.

Must run after check-assignment.cjs; inputs/output stay private. No golden update.
Complete original heap digests are reconstructed by overlaying only slot zero.
This verifies the declared projection, not unrepresented original lifecycles.
"""
import argparse
import copy
import json
import struct
from pathlib import Path
from pc_r10_assignment_projection import canonical, project
from pc_r10_projection_inventory import Memory, digest, load, require

ORACLE = '504f4f1142597f4f8e451e15837383df2527a2afc921149e4f72d75a8fb8d877'
FIXTURE = '39ec04463f83c893e3ab702a6d29d31bd95ee925b06d7a3e70d149a85e9075ea'


def verify_event(response, original, fixture, expected_heap):
    require(response['ok'] is True, 'Rust request rejected')
    event, world = response['result'], response['state']
    kind, candidate = original['kind'], original['candidate']
    value = -1 if candidate is None else fixture['members'][candidate]
    require(world['fixture'] == fixture and world['fixture_sha256'] == FIXTURE,
            'immutable projection changed')
    require(world['mapping'] == [value]+[-1]*19, 'complete projected mapping differs')
    require(event['club_id'] == fixture['club_id'] and event['slot'] == 0 and
            event['rng_draws'] == original['rng_draws'] == 0, 'scope or RNG')
    if kind == 'assign':
        require(event['kind'] == 'AssignmentMade' and event['original_return'] == 1 and
                original['returned'] == 'success-one' and event['new_staff_id'] == value,
                'assignment return/member')
        writes = [dict(row_mode=0, byte_offset=2, width=4, value=value)]
        require(original['ordered_writes'] == [dict(field='slot_zero', width=4, candidate=candidate)]
                and original['ordered_write_pcs'] == ['00896b98'], 'original assignment effects')
    else:
        require(event['kind'] == 'AssignmentReadBack', 'readback kind')
        expected = dict(kind='Empty') if candidate is None else dict(kind='StaffId', staff_id=value)
        require(event['readback'] == expected and original['returned'] == candidate,
                'readback identity')
        require(original['ordered_writes'] == [] and original['ordered_write_pcs'] == [],
                'original readback effects')
        writes = []
    require(event['ordered_writes'] == writes, 'ordered effects differ')
    require(original['heap_sha256'] == expected_heap[value], 'complete original heap differs')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('oracle', type=Path)
    p.add_argument('corpus', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    oracle_raw = args.oracle.read_bytes()
    require(digest(oracle_raw) == ORACLE, 'original receipt identity')
    oracle = json.loads(oracle_raw)
    memory = Memory(load(args.capture, 'retained'))
    fixture, _ = project(memory)
    require(digest(canonical(fixture)) == FIXTURE, 'reviewed fixture identity')
    corpus = json.loads(args.corpus.read_bytes())
    require(corpus['fixture_sha256'] == FIXTURE, 'corpus fixture identity')
    operations, responses = corpus['operations'], corpus['responses']
    require(len(operations) == len(responses), 'complete corpus cardinality')
    expected_kinds = ['read','assign','read','assign','read','assign','read',
                      'assign','read','assign','read']
    selected = [(op, response) for op, response in zip(operations, responses)
                if op['action'] in ('assignment_command','assignment_readback_command')][:11]
    require(len(selected) == len(oracle['cases']) == 11 and oracle['successful_calls'] == 11,
            'eleven actual original calls required')
    require(oracle['censored_calls'] == 4 and len(oracle['defect_controls']) == 12 and
            all(oracle['defect_controls'].values()), 'retained probes/controls')
    require(oracle['cases'][7:9] == oracle['cases'][9:11], 'original checkpoint suffix')
    cb, mapping = memory.u32(0xae23b4), memory.u32(memory.u32(0xde1d08)+0x601)
    require(memory.i32(cb+fixture['club_id']*581) == fixture['club_id'], 'club binding')
    base, heap = memory.ranges[1]
    target = mapping+fixture['club_id']*145+2-base
    require(0 <= target <= len(heap)-4, 'slot heap extent')
    expected_heap = {}
    for value in [-1]+fixture['members']:
        raw = bytearray(heap)
        struct.pack_into('<i', raw, target, value)
        expected_heap[value] = digest(struct.pack('<II', base, len(raw))+raw)
    for i, ((op, response), original) in enumerate(zip(selected, oracle['cases'])):
        require(original['kind'] == expected_kinds[i], 'original ordered sequence')
        require(op['action'] == ('assignment_command' if original['kind']=='assign'
                                else 'assignment_readback_command'), 'Rust ordered sequence')
        verify_event(response, original, fixture, expected_heap)
    # Deliberate observable defects must fail the same comparator.
    controls = {}
    mutations = {
        'wrong-member': lambda r: r['result'].update(new_staff_id=fixture['members'][1]),
        'wrong-slot': lambda r: r['result'].update(slot=1),
        'wrong-width': lambda r: r['result']['ordered_writes'][0].update(width=1),
        'wrong-row': lambda r: r['result']['ordered_writes'][0].update(row_mode=1),
        'wrong-offset': lambda r: r['result']['ordered_writes'][0].update(byte_offset=6),
        'omit-repeated-write': lambda r: r['result'].update(ordered_writes=[]),
        'extra-rng': lambda r: r['result'].update(rng_draws=1),
        'untouched-slot': lambda r: r['state']['mapping'].__setitem__(1,fixture['members'][0]),
    }
    for name, mutate in mutations.items():
        response = copy.deepcopy(selected[3][1]); mutate(response)
        try:
            verify_event(response, oracle['cases'][3], fixture, expected_heap)
        except ValueError:
            controls[name] = 'detected'
        else:
            raise ValueError('undetected defect: '+name)
    response = copy.deepcopy(selected[2][1])
    response['result']['ordered_writes'] = [dict(row_mode=0, byte_offset=2, width=4,value=-1)]
    try:
        verify_event(response, oracle['cases'][2], fixture, expected_heap)
    except ValueError:
        controls['readback-mutation'] = 'detected'
    else:
        raise ValueError('undetected readback mutation')
    receipt = dict(kind='bounded-assignment-original-effects-comparison-v1',
                   oracle_sha256=ORACLE, fixture_sha256=FIXTURE,
                   corpus_sha256=digest(args.corpus.read_bytes()), calls_compared=11,
                   complete_heap_states=3, defect_controls=controls,
                   limitation='Declared projection/retained initialized lifetime only; no new original execution')
    with args.output.open('xb') as stream:
        stream.write(canonical(receipt)+b'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
