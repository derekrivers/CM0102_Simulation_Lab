#!/usr/bin/env python3
"""Qualify fixed registry option 2 against pinned official instructions and real state.

No game launch, code patches, stubs, synthetic binding, or automatic admission.
Outputs are sanitized; the optional schema-2 fixture remains private.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import capstone
from qualify_human_registry import (Oracle, Snapshot, locate, checked, canonical,
    digest, require, SPECIMEN, SOURCE_CAPTURE, IMAGE_HASH, HEAP_HASH, REGISTRY_STRIDE,
    SLOT_STRIDE, STACK)
from qualify_fresh_human_registry import SparseSnapshot

FRESH_CAPTURE = '014808018f7b20f60abaac5c71a0c509747259e309563650afe0d0cc79da6f40'
BUILD_RECEIPT = '4c7b536403fb545303de05350bebb262126382cea65025b843da1c55a43c0bf5'
INNER_IDENTITIES = {
    'retained': '986a2f582095c698413a6ab617a8c487bf0dfb78a7b7e953f7d83b282af7dc6d',
    'fresh': '15697cfbb10725a20c50a8bb290ff8fe85fd05c572d8f7302d4ddbc95e842dc2'}
PRODUCER_VALUES = [0, 0, 1, 1, 0, 1, 0]
MIXED = [('RegistryOptionTwoSet', 1), ('HumanSlotSelected', 1),
         ('RegistryOptionTwoSet', 0), ('HumanSlotSelected', 0),
         ('RegistryOptionTwoSet', 0), ('HumanSlotSelected', 1),
         ('RegistryOptionTwoSet', 1), ('HumanSlotSelected', 1),
         ('RegistryOptionTwoSet', 0), ('HumanSlotSelected', 0)]
RANGES = {0x5feb60: (0x5feb60, 0x5fed42),
          0x5fbe20: (0x5fbe20, 0x5fc004), 0x5fbd00: (0x5fbd00, 0x5fbe11)}
SELECTOR_CALLEES = [(0x5409b0, 0x540a4c), (0x53b900, 0x53b99f)]


class ProducerOracle(Oracle):
    """Narrow each call's reads/instructions; preserve the complete captured state."""
    def __init__(self, raw, snapshot, state):
        require(capstone.__version__ == '5.0.7', 'requires Capstone 5.0.7')
        super().__init__(raw, snapshot, state)
        self.decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.active_entry = None
        self.ordered_reads = []
        self.current_starts = set()
        s = state
        self.fields = {
            'staff_count': (0xae2364, 4), 'club_count': (0xae235c, 4),
            'nation_count': (0xae2350, 4), 'club_id': (s['club'], 4),
            'club_manager': (s['club']+0xcf, 4),
            'manager_id': (s['manager'], 4), 'registry_base': (s['registry'], 4),
            'registry_count': (s['registry']+4, 4),
            'selected_slot': (s['row']+0x9a69, 1)}

    def instruction(self, uc, address, size, _):
        ranges = [RANGES[self.active_entry]]
        if self.active_entry == 0x5fbe20:
            ranges += SELECTOR_CALLEES
        require(any(start <= address and address+size <= end for start, end in ranges),
                'unqualified instruction '+hex(address))
        decoded = list(self.decoder.disasm(bytes(uc.mem_read(address, size)), address))
        require(len(decoded) == 1 and decoded[0].size == size, 'instruction decode mismatch')
        require(decoded[0].mnemonic not in ('int', 'syscall', 'sysenter'),
                'unqualified system boundary '+hex(address))
        if decoded[0].mnemonic == 'call':
            require(self.active_entry == 0x5fbe20 and
                    decoded[0].op_str in ('0x5409b0', '0x53b900'),
                    'unqualified call boundary '+hex(address))
        self.starts.add(address)
        self.current_starts.add(address)

    def read(self, uc, access, address, size, value, _):
        if STACK <= address and address+size <= STACK+0x10000:
            return
        names = [name for name, extent in self.fields.items()
                 if extent == (address, size) and name in self.admitted_fields]
        require(len(names) == 1, 'unqualified non-stack read')
        self.reads.add((address, size))
        self.ordered_reads.append({'field': names[0], 'width': size})

    def call(self, entry, arguments, receiver, allowed=(), expected=None):
        require(entry in RANGES, 'unsupported entry')
        self.active_entry = entry
        self.admitted_fields = {'manager_id', 'staff_count', 'registry_base', 'registry_count'}
        if entry == 0x5fbe20:
            self.admitted_fields |= {'club_count', 'nation_count', 'club_id', 'club_manager'}
        if entry == 0x5fbd00:
            self.admitted_fields |= {'selected_slot'}
        self.ordered_reads = []
        self.current_starts = set()
        value, result = super().call(entry, arguments, receiver, allowed, expected)
        result['ordered_non_stack_reads'] = copy.deepcopy(self.ordered_reads)
        result['instruction_starts'] = len(self.current_starts)
        result['no_system_instruction'] = True
        result['only_qualified_original_calls'] = True
        result['no_call_instruction'] = entry != 0x5fbe20
        return value, result


def fixture(snapshot, s, source):
    row = s['row']
    inner = {'schema_version': 1, 'origin': 'captured-bosman-human-registry',
             'source_capture_sha256': SOURCE_CAPTURE if source == 'retained' else FRESH_CAPTURE,
             'specimen_sha256': SPECIMEN, 'club_count': s['clubs'],
             'ordinary_club_limit': s['clubs']-2*s['nations'], 'staff_count': s['staff'],
             'registry_count': s['registry_count'], 'club_id': s['club_id'],
             'manager_id': s['manager_id'], 'registry_index': s['registry_index'],
             'selected_slot': snapshot.read(row+0x9a69, 1)[0],
             'registry_row_sha256': digest(snapshot.read(row, REGISTRY_STRIDE))}
    require(digest(canonical(inner)) == INNER_IDENTITIES[source], 'inner fixture mismatch')
    guard = snapshot.u32(row+0x9a01)
    option = snapshot.read(row+0x9b25, 1)[0]
    require(guard in (0, 1) and option in (0, 1) and inner['selected_slot'] in (0, 1),
            'unsupported initial registry state')
    return {'schema_version': 2, 'human': inner, 'guard_9a01': guard, 'option_two': option}


def generate(binary, capture, source, build_receipt=None):
    raw = checked(binary, SPECIMEN)
    if source == 'retained':
        snapshot = Snapshot(capture)
        identity = {'source_capture_sha256': SOURCE_CAPTURE, 'image_sha256': IMAGE_HASH,
                    'heap_sha256': HEAP_HASH,
                    'platform_revision': 'f9583098d39c77ac6982a5aa9daec56d74454531'}
    else:
        require(build_receipt is not None, 'fresh input requires sealed build receipt')
        metadata = json.loads(checked(build_receipt, BUILD_RECEIPT))
        snapshot = SparseSnapshot(capture, FRESH_CAPTURE)
        identity = {'source_capture_sha256': FRESH_CAPTURE,
                    'build_receipt_sha256': BUILD_RECEIPT,
                    'platform_revision': metadata['source']['revision'],
                    'instrumented_binary_sha256': metadata['instrumented']['sha256'],
                    'captured_regions': len(snapshot.regions)}
    s = locate(snapshot)
    projected = fixture(snapshot, s, source)
    oracle = ProducerOracle(raw, snapshot, s)
    selected = projected['human']['selected_slot']
    option = projected['option_two']
    producer_cases, mixed_cases = [], []

    def execute(kind, value):
        nonlocal selected, option
        require(kind in ('RegistryOptionTwoSet', 'HumanSlotSelected') and value in (0, 1),
                'unsupported research command')
        previous_slot, previous_value = selected, option
        if kind == 'RegistryOptionTwoSet':
            _, call = oracle.call(0x5feb60, [2, value, s['manager']], s['registry'],
                [(s['row']+0x9b25, 1)], (s['registry_index']*8547 & 0xffffff00) | 2)
            offset = 0x9b25
            option = value
        else:
            _, call = oracle.call(0x5fbe20, [value, s['club'], s['manager']], s['registry'],
                [(s['row']+0x9a69, 1)], s['registry_base'] if value else s['registry_index']*8547)
            _, resolver = oracle.call(0x5fbd00, [s['manager']], s['registry'],
                                     expected=s['row']+value*SLOT_STRIDE)
            require(resolver['ordered_writes'] == [], 'resolver wrote state')
            offset = 0x9a69
            selected = value
        expected = [{'registry_offset': offset, 'width': 1, 'value': value}]
        require(call['ordered_writes'] == expected, 'ordered effect mismatch')
        oracle.full_state({0x9a69: selected, 0x9b25: option})
        result = {'kind': kind, 'previous_slot': previous_slot, 'selected_slot': selected,
                  'previous_value': previous_value, 'option_two': option,
                  'ordered_writes': expected, 'rng_draws': 0}
        result['value' if kind == 'RegistryOptionTwoSet' else 'slot'] = value
        return result

    for value in PRODUCER_VALUES:
        case = execute('RegistryOptionTwoSet', value)
        producer_cases.append({'value': value, 'previous_value': case['previous_value'],
                              'new_value': case['option_two'], 'ordered_writes': case['ordered_writes'],
                              'rng_draws': 0})
    require(option == projected['option_two'] and selected == projected['human']['selected_slot'],
            'producer corpus must restore actual initial state')
    for kind, value in MIXED:
        mixed_cases.append(execute(kind, value))

    # Exact entire captured state continuation, with an interleaved checkpoint.
    # Every call resets ABI inputs; this is an emulator checkpoint, not a savegame.
    prefix = [('RegistryOptionTwoSet', 1), ('HumanSlotSelected', 1)]
    suffix = [('RegistryOptionTwoSet', 0), ('HumanSlotSelected', 0),
              ('RegistryOptionTwoSet', 0), ('HumanSlotSelected', 1)]
    for kind, value in prefix:
        execute(kind, value)
    checkpoint = oracle.capture_state()
    checkpoint_selected, checkpoint_option = selected, option
    first = [execute(kind, value) for kind, value in suffix]
    first_state = oracle.capture_state()
    oracle.restore_state(checkpoint)
    selected, option = checkpoint_selected, checkpoint_option
    second = [execute(kind, value) for kind, value in suffix]
    require(first == second and oracle.capture_state() == first_state,
            'complete checkpoint continuation mismatch')

    controls = {}
    observed = [c['ordered_writes'][0] for c in producer_cases]
    def changed(name, mutation):
        candidate = copy.deepcopy(observed)
        mutation(candidate)
        controls[name] = sum(a != b for a, b in zip(observed, candidate))
    changed('wrong-offset', lambda xs: [x.update(registry_offset=0x9b24) for x in xs])
    changed('wrong-row', lambda xs: [x.update(registry_offset=x['registry_offset']-REGISTRY_STRIDE) for x in xs])
    changed('word-instead-of-byte', lambda xs: [x.update(width=2) for x in xs])
    changed('inverted-value', lambda xs: [x.update(value=1-x['value']) for x in xs])
    controls['omitted-write'] = sum(bool(c['ordered_writes']) for c in producer_cases)
    controls['elided-repeated-value-write'] = sum(c['previous_value'] == c['value']
                                                and bool(c['ordered_writes']) for c in producer_cases)
    controls['extra-rng-draw'] = sum(c['rng_draws'] != 1 for c in producer_cases)
    ordered = [c['ordered_writes'][0] for c in mixed_cases]
    controls['reordered-mixed-writes'] = int(ordered != [ordered[1], ordered[0]]+ordered[2:])
    controls['option-command-changes-slot'] = sum(c['selected_slot'] != 1-c['previous_slot']
        for c in mixed_cases if c['kind'] == 'RegistryOptionTwoSet')
    controls['slot-command-changes-option'] = sum(c['option_two'] != 1-c['previous_value']
        for c in mixed_cases if c['kind'] == 'HumanSlotSelected')
    # Prove the full-state checker detects an unrelated row-byte corruption.
    saved = bytes(oracle.uc.mem_read(s['row']+0x9a01, 4))
    oracle.uc.mem_write(s['row']+0x9a01, bytes([saved[0]^1])+saved[1:])
    try:
        oracle.full_state({0x9a69: selected, 0x9b25: option})
    except ValueError:
        controls['immutable-guard-corruption'] = 1
    else:
        raise ValueError('full state control failed')
    finally:
        oracle.uc.mem_write(s['row']+0x9a01, saved)
    oracle.full_state({0x9a69: selected, 0x9b25: option})
    rejected = []
    for value in (-1, 2, 256):
        try:
            execute('RegistryOptionTwoSet', value)
        except ValueError as error:
            require(str(error) == 'unsupported research command', 'wrong rejection boundary')
            rejected.append(value)
        else:
            raise ValueError('unsupported host domain accepted')
    oracle.full_state({0x9a69: selected, 0x9b25: option})
    controls['unsupported-host-value-before-execution'] = len(rejected)
    require(all(controls.values()), 'non-discriminating negative control')
    successful_starts = len(oracle.starts)
    successful_calls = copy.deepcopy(oracle.calls)

    # Probes are censored at strict boundaries, never rejection parity. Permit
    # option3's first write so its partial mutation remains visible in the receipt.
    probes = []
    baseline = oracle.capture_state()
    for name, args, writes in [
        ('null-manager-current-context', [2, 1, 0], []),
        ('nonhuman-manager-diagnostics', [2, 1, s['manager']-16*110], []),
        ('option-three-larger-path', [3, 1, s['manager']], [(s['row']+0x9b26, 1)])]:
        oracle.restore_state(baseline)
        try:
            oracle.call(0x5feb60, args, s['registry'], writes)
        except ValueError as error:
            reason = str(error)
            probes.append({'name': name, 'execution_status': 'censored',
                           'comparison_verdict': 'not-comparable',
                           'first_boundary': reason,
                           'partial_ordered_writes': copy.deepcopy(oracle.writes)})
        else:
            raise ValueError('unsupported original path unexpectedly returned')
    oracle.restore_state(baseline)
    oracle.full_state({0x9a69: selected, 0x9b25: option})
    calls_by_entry = {}
    for call in successful_calls:
        calls_by_entry.setdefault(call['entry'], []).append(call)
    return {
        'schema_version': 1, 'specimen_sha256': SPECIMEN,
        'emulator': 'unicorn 2.1.4', 'decoder': 'capstone 5.0.7',
        'method': 'official entry-to-return instructions; real initialized binding; no code patches or stubbed callees',
        'capture': identity,
        'supported_domain': {'producer_entry': '005feb60', 'fixed_option': 2,
            'values': [0, 1], 'nonnull_reciprocal_ordinary_human_binding': True,
            'initial_guard_dword_9a01': projected['guard_9a01'],
            'initial_option_byte_9b25': projected['option_two'],
            'initial_slot_byte_9a69': projected['human']['selected_slot'],
            'registry_rows': s['registry_count'], 'registry_stride': REGISTRY_STRIDE,
            'guard_is_immutable': True, 'outer_getter_invoked': False},
        'private_fixture': {'sha256': digest(canonical(projected)),
            'bytes': len(canonical(projected)), 'inner_sha256': INNER_IDENTITIES[source],
            'registry_row_sha256': projected['human']['registry_row_sha256'],
            'production_admission': 'pending independent review; not self-admitted'},
        'instruction_ranges': [{'entry': f'{entry:08x}', 'start': f'{a:08x}',
            'end_exclusive': f'{b:08x}', 'sha256': digest(bytes(oracle.uc.mem_read(a, b-a)))}
            for entry, (a, b) in list(RANGES.items())+[(a, (a, b)) for a, b in SELECTOR_CALLEES]],
        'successful_calls': len(successful_calls), 'successful_instruction_starts': successful_starts,
        'call_evidence': calls_by_entry, 'producer_cases': producer_cases, 'mixed_cases': mixed_cases,
        'checkpoint_continuation': {'equal': True, 'prefix': prefix, 'suffix': suffix,
            'entire_captured_state_equal': True, 'ordered_effects_equal': True,
            'original_savegame_claim': False},
        'captured_state_bytes': sum(len(data) for _, data in oracle.segments),
        'complete_captured_state_and_official_image_checked_after_every_supported_command': True,
        'supported_rng_draws': 0, 'defect_controls': controls, 'unsupported_original_probes': probes,
        'limitations': [
            'Boolean fixed option2 only; no gameplay meaning assigned',
            'Explicit manager and initialized registry only; no lifecycle or appointment claim',
            'No outer getter/UI handler, original savegame or full-game parity claim',
            'Typed host rejection is not original rejection parity; original stores the low byte',
            'Stack scratch is synthetic ABI setup; full captured regions and loaded official image remain checked',
            'Historical capture lacks contemporaneous consumption seal' if source == 'retained' else
            'Sparse regions only; R5 execution/seals do not establish actual file-open/consumption parity']
    }, projected


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source', choices=('retained', 'fresh'), required=True)
    parser.add_argument('--build-receipt', type=Path)
    parser.add_argument('--private-fixture', type=Path)
    args = parser.parse_args()
    receipt, projected = generate(args.binary, args.capture, args.source, args.build_receipt)
    with args.output.open('x', encoding='utf8') as out:
        out.write(json.dumps(receipt, indent=2)+'\n')
    if args.private_fixture:
        fd = os.open(args.private_fixture, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as out:
            out.write(canonical(projected))
    print(json.dumps({'successful_calls': receipt['successful_calls'],
                      'successful_instruction_starts': receipt['successful_instruction_starts'],
                      'receipt_sha256': digest(args.output.read_bytes()),
                      'fixture_sha256': digest(canonical(projected))}))
