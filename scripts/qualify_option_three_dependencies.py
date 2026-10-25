#!/usr/bin/env python3
"""Bounded option-three dependency diagnostics; no original process or admission."""
import argparse
import copy
import json
from pathlib import Path
import capstone
from unicorn.x86_const import UC_X86_REG_EIP
from qualify_human_registry import (Oracle, Snapshot, locate, checked, digest,
    require, canonical, SPECIMEN, SOURCE_CAPTURE, IMAGE_HASH, HEAP_HASH, STACK, RANGES)
from qualify_fresh_human_registry import SparseSnapshot
from qualify_human_registry_producer import FRESH_CAPTURE, BUILD_RECEIPT, fixture


class Boundary(ValueError):
    pass


class DependencyOracle(Oracle):
    def __init__(self, raw, snapshot, state, connected):
        super().__init__(raw, snapshot, state)
        require(capstone.__version__ == '5.0.7', 'decoder version')
        self.decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.connected = connected
        self.pc = None
        self.decoded = None
        self.boundary = None
        self.ordered_reads = []
        self.fields = {
            'manager_id': (state['manager'], 4),
            'staff_count': (0xae2364, 4),
            'registry_base': (state['registry'], 4),
            'registry_count': (state['registry']+4, 4)}

    def censor(self, kind, category, width=None):
        self.boundary = {'kind': kind, 'pc': f'{self.pc:08x}',
            'instruction': self.decoded, 'region_category': category,
            'access_width': width}
        raise Boundary('frozen dependency boundary')

    def instruction(self, uc, address, size, _):
        self.pc = address
        decoded = list(self.decoder.disasm(bytes(uc.mem_read(address, size)), address))
        require(len(decoded) == 1 and decoded[0].size == size, 'decode mismatch')
        ins = decoded[0]
        self.decoded = ins.mnemonic + (' '+ins.op_str if ins.op_str else '')
        ranges = RANGES if self.connected else [(0x5feb60, 0x5fed42)]
        if not any(a <= address and address+size <= b for a, b in ranges):
            self.censor('instruction', 'unqualified-resolver-code')
        if ins.mnemonic in ('int', 'syscall', 'sysenter'):
            self.censor('system-instruction', 'system-boundary')
        self.starts.add(address)

    def read(self, uc, access, address, size, value, _):
        if STACK <= address and address+size <= STACK+0x10000:
            return
        manager_club = address == self.state['manager']+0x39
        field = next((k for k, v in self.fields.items() if v == (address, size)), None)
        if field is None:
            if manager_club and size == 4 and self.connected:
                field = 'manager_club'
            elif self.connected and any(a <= address and address+size <= b
                                       for a, b in self.read_ranges):
                field = 'existing-r4-outer-field'
            else:
                self.censor('read', 'manager-club-field' if manager_club else
                            'outside-frozen-field-domain', size)
        self.reads.add((address, size))
        self.ordered_reads.append({'field': field, 'width': size})

    def write(self, uc, access, address, size, value, _):
        if STACK <= address and address+size <= STACK+0x10000:
            return
        if (address, size) not in self.allowed_writes:
            self.censor('write', 'outside-frozen-write-domain', size)
        super().write(uc, access, address, size, value, _)


def generate(binary, capture, source, build_receipt=None):
    raw = checked(binary, SPECIMEN)
    if source == 'retained':
        snapshot = Snapshot(capture)
        identity = {'source_capture_sha256': SOURCE_CAPTURE,
                    'image_sha256': IMAGE_HASH, 'heap_sha256': HEAP_HASH}
    else:
        require(build_receipt is not None, 'sealed build receipt required')
        checked(build_receipt, BUILD_RECEIPT)
        snapshot = SparseSnapshot(capture, FRESH_CAPTURE)
        identity = {'source_capture_sha256': FRESH_CAPTURE,
                    'build_receipt_sha256': BUILD_RECEIPT}
    state = locate(snapshot)
    projected = fixture(snapshot, state, source)
    cases = []
    for connected in (False, True):
        oracle = DependencyOracle(raw, snapshot, state, connected)
        checkpoint = oracle.capture_state()
        for value in (0, 1):
            oracle.restore_state(checkpoint)
            oracle.boundary = None
            oracle.ordered_reads = []
            oracle.starts = set()
            expected = (state['registry_index']*8547 & 0xffffff00) | 3
            try:
                _, result = oracle.call(0x5feb60, [3, value, state['manager']],
                    state['registry'], [(state['row']+0x9b26, 1)] +
                    ([(state['row']+0x9a69, 1)] if connected else []),
                    expected if value == 0 else None)
            except Boundary:
                require(value == 1, 'zero branch unexpectedly censored')
                status, verdict, abi = 'censored', 'not-comparable', False
            else:
                require(value == 0, 'nonzero path escaped frozen boundary')
                status, verdict, abi = 'succeeded', 'matched-bounded-effects', True
            expected_writes = [{'registry_offset': 0x9b26, 'width': 1, 'value': value}]
            if connected and value == 1 and source == 'fresh':
                expected_writes.append({'registry_offset': 0x9a69, 'width': 1, 'value': 0})
            require(oracle.writes == expected_writes, 'partial ordered effects mismatch')
            oracle.full_state({w['registry_offset']: w['value'] for w in expected_writes})
            if value:
                require(oracle.boundary['pc'] == ('008968f0' if connected else '005fec2e'),
                        'unexpected first boundary')
            cases.append({'admission': 'connected-r4' if connected else 'strict-producer',
                'value': value, 'execution_status': status, 'comparison_verdict': verdict,
                'first_boundary': copy.deepcopy(oracle.boundary),
                'ordered_partial_effects': copy.deepcopy(oracle.writes),
                'ordered_admitted_reads': copy.deepcopy(oracle.ordered_reads),
                'instruction_starts': len(oracle.starts), 'return_and_abi_checked': abi,
                'complete_captured_state_and_image_checked': True,
                'rng_draws': 0 if abi else None})
        oracle.restore_state(checkpoint)
        oracle.full_state({})
    strict = cases[1]
    controls = {
        'lost-initial-partial-write': strict['ordered_partial_effects'] != [],
        'wrong-width': strict['first_boundary']['access_width'] != 1,
        'wrong-pc': strict['first_boundary']['pc'] != '005fec19',
        'wrong-region': strict['first_boundary']['region_category'] != 'registry-row',
        'wrong-instruction': strict['first_boundary']['instruction'] != 'nop',
        'false-completed-abi': strict['return_and_abi_checked'] is False,
        'zero-branch-admission-invariance': all(cases[i][key] == cases[i+2][key]
            for i in (0,) for key in ('ordered_partial_effects', 'return_and_abi_checked',
                                      'ordered_admitted_reads', 'instruction_starts'))}
    if source == 'fresh':
        controls['lost-outer-selector-write'] = len(cases[3]['ordered_partial_effects']) == 2
    require(all(controls.values()), 'nondiscriminating diagnostic control')
    return {'schema_version': 1, 'source': source, 'specimen_sha256': SPECIMEN,
        'qualifier_sha256': digest(Path(__file__).read_bytes()),
        'capture': identity, 'wrapper_sha256': digest(canonical(projected)),
        'emulator': 'unicorn 2.1.4', 'decoder': 'capstone 5.0.7',
        'calls': cases, 'defect_controls': controls,
        'budget': {'calls': 4, 'instruction_limit_per_call': 3000,
                   'emulator_timeout_microseconds_per_call': 100000},
        'immutable_inputs': True, 'production_admission': 'none',
        'nonzero_entry_to_return_qualified': False,
        'continuation_qualified': False,
        'limitations': ['No original process or UI/gameplay claim',
            'No lifetime/general-manager or nonzero completion/RNG claim',
            'Static downstream dependencies are not executed qualification']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source', choices=('retained', 'fresh'), required=True)
    parser.add_argument('--build-receipt', type=Path)
    args = parser.parse_args()
    # Reserve the new output before execution; failed attempts never disappear.
    with args.output.open('x', encoding='utf8') as output:
        try:
            result = generate(args.binary, args.capture, args.source, args.build_receipt)
        except Exception as error:
            output.write(json.dumps({'execution_status': 'failed',
                'error_type': type(error).__name__,
                'comparison_verdict': 'not-comparable'})+'\n')
            raise
        output.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'source': args.source, 'calls': len(result['calls']),
                      'receipt_sha256': digest(args.output.read_bytes())}))
