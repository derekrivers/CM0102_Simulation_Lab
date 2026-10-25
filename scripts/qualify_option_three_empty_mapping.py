#!/usr/bin/env python3
"""Exact initialized option-three path with sixteen captured empty mapping slots."""
import argparse
import copy
import json
import time
from pathlib import Path
from qualify_option_three_dependencies import DependencyOracle, capstone, unicorn, sys
from qualify_human_registry import (Snapshot, locate, checked, canonical, digest,
    require, SPECIMEN, SOURCE_CAPTURE, IMAGE_HASH, HEAP_HASH, STACK)
from qualify_fresh_human_registry import SparseSnapshot
from qualify_human_registry_producer import FRESH_CAPTURE, BUILD_RECEIPT, fixture

CALLS = {0x5fec42: 0x896660, 0x5fec69: 0x8968f0,
    0x89695c: 0x8982b0, 0x8982c8: 0x600a50,
    0x8966e7: 0x600a50, 0x896700: 0x5fd210, 0x896718: 0x5fea50,
    0x896737: 0x5fbe20, 0x896749: 0x5fbd00, 0x600b84: 0x53b900,
    0x5fbe81: 0x5409b0, 0x5fbec9: 0x53b900, 0x5fbf06: 0x53b900}


class EmptyMappingOracle(DependencyOracle):
    def __init__(self, raw, snapshot, state):
        super().__init__(raw, snapshot, state, True)
        self.fields['manager_club'] = (state['manager']+0x39, 4)
        for index in range(16):
            self.fields[f'empty_mapping_slot_{index}'] = (
                state['mapping']+state['club_id']*145+2+index*4, 4)
        self.current_starts = set()
        self.write_pcs = []

    def instruction(self, uc, address, size, unused):
        # Only these two exact additional original code ranges are admitted.
        self.pc = address
        ins = list(self.decoder.disasm(bytes(uc.mem_read(address, size)), address))
        require(len(ins) == 1 and ins[0].size == size, 'decode mismatch')
        self.decoded = ins[0].mnemonic + (' '+ins[0].op_str if ins[0].op_str else '')
        if ins[0].mnemonic == 'call' and (address not in CALLS or
                ins[0].op_str != hex(CALLS[address])):
            self.censor('call', 'unqualified-original-call')
        if 0x8968f0 <= address and address+size <= 0x896a8e or \
                0x8982b0 <= address and address+size <= 0x8983ed:
            self.starts.add(address)
        else:
            super().instruction(uc, address, size, unused)
        self.current_starts.add(address)

    def write(self, uc, access, address, size, value, unused):
        super().write(uc, access, address, size, value, unused)
        if not (STACK <= address and address+size <= STACK+0x10000):
            self.write_pcs.append(f'{self.pc:08x}')


def effects(value, source):
    result = [{'registry_offset': 0x9b26, 'width': 1, 'value': value}]
    if value:
        if source == 'fresh':
            result.append({'registry_offset': 0x9a69, 'width': 1, 'value': 0})
        for index in range(16):
            for offset in (0x9b28, 0x9b2c):
                result.append({'registry_offset': offset+8*index, 'width': 4,
                               'value': 0xffffffff})
    return result


def verify(case, source):
    require(case['ordered_writes'] == effects(case['value'], source), 'effects differ')
    require(case['rng_draws'] == 0, 'RNG claim differs')
    require(case['return_and_abi_checked'] is True, 'ABI differs')
    require(case['complete_state_and_image_checked'] is True, 'state differs')


def generate(binary, capture, source, build_receipt, attempts):
    raw = checked(binary, SPECIMEN)
    if source == 'retained':
        snapshot = Snapshot(capture)
        identity = {'source_capture_sha256': SOURCE_CAPTURE,
                    'image_sha256': IMAGE_HASH, 'heap_sha256': HEAP_HASH}
    else:
        checked(build_receipt, BUILD_RECEIPT)
        snapshot = SparseSnapshot(capture, FRESH_CAPTURE)
        identity = {'source_capture_sha256': FRESH_CAPTURE,
                    'build_receipt_sha256': BUILD_RECEIPT}
    state = locate(snapshot)
    projected = fixture(snapshot, state, source)
    for index in range(16):
        require(snapshot.s32(state['mapping']+state['club_id']*145+2+index*4) == -1,
                'requires actual sixteen empty mapping slots')
    oracle = EmptyMappingOracle(raw, snapshot, state)
    changed = {}
    cases = []
    def run(value):
        oracle.ordered_reads = []
        oracle.current_starts = set()
        oracle.write_pcs = []
        attempt = {'value': value, 'execution_status': 'started'}
        attempts.append(attempt)
        expected = effects(value, source)
        started = time.monotonic()
        try:
            _, result = oracle.call(0x5feb60, [3, value, state['manager']], state['registry'],
                [(state['row']+w['registry_offset'], w['width']) for w in expected],
                0xffffffff if value else (state['registry_index']*8547 & 0xffffff00) | 3)
        finally:
            attempt.update(ordered_partial_effects=copy.deepcopy(oracle.writes),
                first_boundary=copy.deepcopy(oracle.boundary),
                last_pc=f'{oracle.pc:08x}' if oracle.pc is not None else None,
                decoded_instruction=oracle.decoded,
                ordered_admitted_reads=copy.deepcopy(oracle.ordered_reads),
                emulation_elapsed_seconds=time.monotonic()-started)
        for write in expected:
            for i, byte in enumerate(write['value'].to_bytes(write['width'], 'little')):
                changed[write['registry_offset']+i] = byte
        oracle.full_state(changed)
        case = {'value': value, 'ordered_writes': result['ordered_writes'],
            'ordered_write_pcs': oracle.write_pcs.copy(),
            'ordered_reads': copy.deepcopy(oracle.ordered_reads),
            'instruction_starts': [f'{a:08x}' for a in sorted(oracle.current_starts)],
            'return_and_abi_checked': True, 'complete_state_and_image_checked': True,
            'rng_draws': 0}
        verify(case, source)
        attempt['execution_status'] = 'succeeded'
        cases.append(case)
        return case
    run(1)
    checkpoint, checkpoint_changes = oracle.capture_state(), changed.copy()
    first = run(1)
    final = oracle.capture_state()
    run(0)
    oracle.restore_state(checkpoint)
    changed = checkpoint_changes.copy()
    second = run(1)
    require(first == second and oracle.capture_state() == final, 'continuation differs')
    controls = {}
    for name, mutation in [
        ('omit-initial-write', lambda c: c['ordered_writes'].pop(0)),
        ('omit-loop-write', lambda c: c['ordered_writes'].pop()),
        ('wrong-loop-width', lambda c: c['ordered_writes'][-1].update(width=1)),
        ('wrong-loop-value', lambda c: c['ordered_writes'][-1].update(value=0)),
        ('wrong-loop-offset', lambda c: c['ordered_writes'][-1].update(registry_offset=0x9b27)),
        ('reorder-loop-writes', lambda c: c['ordered_writes'].reverse()),
        ('extra-rng', lambda c: c.update(rng_draws=1)),
        ('unchecked-ABI', lambda c: c.update(return_and_abi_checked=False))]:
        candidate = copy.deepcopy(cases[0])
        mutation(candidate)
        try:
            verify(candidate, source)
        except ValueError:
            controls[name] = True
        else:
            raise ValueError('nondiscriminating mutation')
    dependencies = ['qualify_option_three_empty_mapping.py', 'qualify_option_three_dependencies.py',
        'qualify_human_registry.py', 'qualify_human_registry_producer.py',
        'qualify_fresh_human_registry.py', 'qualify_manager_bound_plan.py']
    return {'schema_version': 1, 'source': source, 'specimen_sha256': SPECIMEN,
        'capture': identity, 'wrapper_sha256': digest(canonical(projected)),
        'source_dependencies': {name: digest((Path(__file__).parent/name).read_bytes())
                                for name in dependencies},
        'upstream_lock_sha256': digest((Path(__file__).parent.parent/'config/upstream-lock.json').read_bytes()),
        'tools': {name: digest(Path(path).read_bytes()) for name, path in
                  [('python', sys.executable), ('capstone_module', capstone.__file__),
                   ('unicorn_module', unicorn.__file__)]},
        'emulator': 'unicorn 2.1.4', 'decoder': 'capstone 5.0.7',
        'domain': 'exact initialized ordinary human binding; sixteen mapping entries equal -1',
        'cases': cases, 'defect_controls': controls,
        'successful_calls': 4, 'full_nonzero_entry_to_return': True,
        'checkpoint_continuation': 'full captured state and ordered results equal',
        'production_admission': 'none', 'rng_draws_per_call': 0,
        'limits': {'instruction_count': 3000, 'emulator_microseconds': 100000},
        'limitations': ['Nonempty mapping and staff-linked lifetime paths unqualified',
            'No constructor/appointment/original-process/UI/save/match claim',
            'Fresh checks all declared sparse regions, not complete runtime memory']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary', type=Path); p.add_argument('capture', type=Path)
    p.add_argument('output', type=Path); p.add_argument('--source', choices=('retained', 'fresh'), required=True)
    p.add_argument('--build-receipt', type=Path)
    a = p.parse_args()
    timing_path = a.output.with_name(a.output.name+'.timing.json')
    require(not a.output.exists() and not timing_path.exists(), 'output exists')
    with a.output.open('x', encoding='utf8') as output, timing_path.open('x', encoding='utf8') as timing:
        attempts = []
        started = time.monotonic()
        try:
            receipt = generate(a.binary, a.capture, a.source, a.build_receipt, attempts)
        except Exception as error:
            output.write(json.dumps({'execution_status': 'failed', 'error_type': type(error).__name__,
                'attempts': attempts, 'comparison_verdict': 'not-comparable'}, indent=2)+'\n')
            raise SystemExit('failed; sanitized attempt retained') from None
        else:
            output.write(json.dumps(receipt, indent=2)+'\n')
        finally:
            timing.write(json.dumps({'host_generate_elapsed_seconds': time.monotonic()-started,
                'attempts': attempts}, indent=2)+'\n')
    print(json.dumps({'source': a.source, 'calls': 4, 'receipt_sha256': digest(a.output.read_bytes())}))
