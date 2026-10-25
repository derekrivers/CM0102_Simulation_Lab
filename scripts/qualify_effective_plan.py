#!/usr/bin/env python3
"""R7 connected official lookup; immutable real captures, no stubs or patches."""
import argparse
import copy
import json
import os
from pathlib import Path
import capstone
from unicorn.x86_const import UC_X86_REG_EIP
from qualify_human_registry import (Oracle, Snapshot, locate, checked, canonical,
    digest, require, SPECIMEN, SOURCE_CAPTURE, IMAGE_HASH, HEAP_HASH, RANGES,
    SLOT_STRIDE, STACK)
from qualify_fresh_human_registry import SparseSnapshot
from qualify_human_registry_producer import fixture as registry_fixture
from qualify_human_registry_producer import FRESH_CAPTURE, BUILD_RECEIPT

# Exact call sites: no arbitrary call admission by enclosing function range.
CALLS = {0x8966e7: 0x600a50, 0x896700: 0x5fd210, 0x896718: 0x5fea50,
         0x896737: 0x5fbe20, 0x896749: 0x5fbd00, 0x600b84: 0x53b900,
         0x5fbe81: 0x5409b0, 0x5fbec9: 0x53b900, 0x5fbf06: 0x53b900}
ACTIVE_ORACLE = None
SEQUENCE = [('lookup', 0), ('lookup', 1), ('select', 1), ('lookup', 0),
            ('option', 1), ('lookup', 0), ('lookup', 1), ('lookup', 1),
            ('select', 0), ('lookup', 1), ('option', 0), ('lookup', 0),
            ('lookup', 1), ('option', 0), ('select', 0), ('lookup', 0)]


class Censored(ValueError):
    def __init__(self, diagnostic, partial_writes):
        self.diagnostic = diagnostic
        self.partial_writes = partial_writes
        super().__init__('censored original boundary')


class EffectiveOracle(Oracle):
    def __init__(self, raw, snapshot, state):
        require(capstone.__version__ == '5.0.7', 'requires Capstone 5.0.7')
        super().__init__(raw, snapshot, state)
        self.decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        s = state
        self.fields = {
            'staff_count': (0xae2364, 4), 'club_count': (0xae235c, 4),
            'nation_count': (0xae2350, 4), 'registry_global': (0xb63c98, 4),
            'club_id': (s['club'], 4), 'club_manager': (s['club']+0xcf, 4),
            'manager_id': (s['manager'], 4), 'registry_base': (s['registry'], 4),
            'registry_count': (s['registry']+4, 4),
            'guard': (s['row']+0x9a01, 4), 'option_two': (s['row']+0x9b25, 1),
            'selected_slot': (s['row']+0x9a69, 1),
            'mapping_pointer': (s['context']+0x601, 4),
            'first_bank_count': (s['context']+0x5fd, 4),
            'first_bank_pointer': (s['context']+0x5f9, 4),
            'mapping_selection': (s['mapping']+s['club_id']*145, 2)}
        self.pc = None
        self.decoded = None
        self.ordered_reads = []
        self.write_instructions = []
        self.current_starts = set()

    def censor(self, category, width=0, field='unadmitted'):
        raise Censored({'instruction': f'{self.pc:08x}', 'category': category,
                        'field': field, 'width': width, 'decoded': self.decoded}, copy.deepcopy(self.writes))

    def instruction(self, uc, address, size, unused):
        self.pc = address
        self.decoded = None
        if not any(a <= address and address+size <= b for a, b in RANGES):
            self.censor('instruction')
        ins = list(self.decoder.disasm(bytes(uc.mem_read(address, size)), address))
        require(len(ins) == 1 and ins[0].size == size, 'decode mismatch')
        self.decoded = {'mnemonic': ins[0].mnemonic, 'instruction_width': size}
        if ins[0].mnemonic in ('int', 'syscall', 'sysenter'):
            self.censor('system_instruction')
        if ins[0].mnemonic == 'call' and (address not in CALLS or
                ins[0].op_str != hex(CALLS[address])):
            self.censor('original_call')
        self.starts.add(address)
        self.current_starts.add(address)

    def read(self, uc, access, address, size, value, unused):
        if STACK <= address and address+size <= STACK+0x10000:
            return
        names = [name for name, extent in self.fields.items() if extent == (address, size)]
        if len(names) != 1:
            category = 'captured_heap' if any(a <= address < a+len(b) for a, b in self.segments) else 'uncaptured_or_image'
            self.censor(category, size)
        self.reads.add((address, size))
        self.ordered_reads.append({'instruction': f'{self.pc:08x}', 'field': names[0], 'width': size})

    def write(self, uc, access, address, size, value, unused):
        if STACK <= address and address+size <= STACK+0x10000:
            return
        if (address, size) not in self.allowed_writes:
            self.censor('write', size)
        super().write(uc, access, address, size, value, unused)
        self.write_instructions.append(f'{self.pc:08x}')

    def call(self, entry, arguments, receiver, allowed=(), expected=None):
        self.ordered_reads = []
        self.write_instructions = []
        self.current_starts = set()
        value, result = super().call(entry, arguments, receiver, allowed, expected)
        result['ordered_non_stack_reads'] = copy.deepcopy(self.ordered_reads)
        result['ordered_write_instructions'] = self.write_instructions.copy()
        result['instruction_starts'] = [f'{a:08x}' for a in sorted(self.current_starts)]
        return value, result


def project(snapshot, state, source):
    s = state
    require((s['first'], s['second'], s['bank_selection']) == (17, 28, 0),
            'unsupported captured ordinary projection')
    return {'schema_version': 3, 'registry': registry_fixture(snapshot, s, source),
            'ordinary': {'first_bank_count': s['first'], 'second_bank_count': s['second'],
                         'selected_plan': s['bank_selection'],
                         'mapping_row_sha256': digest(snapshot.read(s['mapping']+s['club_id']*145, 145)),
                         'first_bank_sha256': digest(snapshot.read(s['bank1'], s['first']*6371)),
                         'second_bank_sha256': digest(snapshot.read(s['bank2'], s['second']*6371))}}


def verify_case(observed, expected):
    require(observed == expected, 'connected case mismatch')


def generate(binary, capture, source, build_receipt=None):
    global ACTIVE_ORACLE
    raw = checked(binary, SPECIMEN)
    if source == 'retained':
        snapshot = Snapshot(capture)
        identity = {'source_capture_sha256': SOURCE_CAPTURE, 'image_sha256': IMAGE_HASH,
                    'heap_sha256': HEAP_HASH}
    else:
        require(build_receipt is not None, 'fresh requires build receipt')
        metadata = json.loads(checked(build_receipt, BUILD_RECEIPT))
        require(metadata['source']['revision'] == '144ed82c248228c7769c6785899527eae5b33c3d', 'wrong platform')
        snapshot = SparseSnapshot(capture, FRESH_CAPTURE)
        identity = {'source_capture_sha256': FRESH_CAPTURE, 'build_receipt_sha256': BUILD_RECEIPT,
                    'instrumented_binary_sha256': metadata['instrumented']['sha256']}
    s = locate(snapshot)
    projected = project(snapshot, s, source)
    registry = projected['registry']
    oracle = EffectiveOracle(raw, snapshot, s)
    ACTIVE_ORACLE = oracle
    selected, option = registry['human']['selected_slot'], registry['option_two']
    guard = registry['guard_9a01']
    require((guard, option, selected) == ((1, 0, 0) if source == 'retained' else (0, 0, 0)), 'initial tuple changed')
    cases = []

    def execute(kind, value):
        nonlocal selected, option
        require(kind in ('lookup', 'select', 'option') and value in (0, 1), 'unsupported command')
        old_slot, old_option = selected, option
        branch, location = None, None
        if kind == 'option':
            expected = (s['registry_index']*8547 & 0xffffff00) | 2
            _, result = oracle.call(0x5feb60, [2, value, s['manager']], s['registry'], [(s['row']+0x9b25, 1)], expected)
            option = value
            writes = [{'registry_offset': 0x9b25, 'width': 1, 'value': value}]
        elif kind == 'select':
            expected = s['registry_base'] if value else s['registry_index']*8547
            _, result = oracle.call(0x5fbe20, [value, s['club'], s['manager']], s['registry'], [(s['row']+0x9a69, 1)], expected)
            _, resolve = oracle.call(0x5fbd00, [s['manager']], s['registry'], expected=s['row']+value*SLOT_STRIDE)
            require(resolve['ordered_writes'] == [], 'resolver mutated')
            selected = value
            writes = [{'registry_offset': 0x9a69, 'width': 1, 'value': value}]
            location = {'kind': 'human_registry', 'registry_index': s['registry_index'], 'slot': value, 'byte_offset': value*SLOT_STRIDE}
        else:
            fallback = guard != 0 and option == 0
            branch = 'ordinary_fallback' if fallback else ('registry_guard_zero' if guard == 0 else 'registry_option_enabled')
            expected = s['bank1'] if fallback else s['row']+value*SLOT_STRIDE
            allowed = [] if fallback else [(s['row']+0x9a69, 1)]
            _, result = oracle.call(0x896660, [s['club'], value], s['context'], allowed, expected)
            writes = [] if fallback else [{'registry_offset': 0x9a69, 'width': 1, 'value': value}]
            if not fallback:
                selected = value
            location = ({'kind': 'ordinary_bank', 'bank': 'first', 'index': 0, 'byte_offset': 0} if fallback else
                        {'kind': 'human_registry', 'registry_index': s['registry_index'], 'slot': value, 'byte_offset': value*SLOT_STRIDE})
        require(result['ordered_writes'] == writes, 'ordered effects differ')
        oracle.full_state({0x9a69: selected, 0x9b25: option})
        expected_case = {'kind': kind, 'value': value, 'previous_slot': old_slot, 'selected_slot': selected,
                'previous_option': old_option, 'option_two': option, 'branch': branch,
                'location': location, 'ordered_writes': writes, 'rng_draws': 0, 'guard_9a01': guard}
        observed_case = copy.deepcopy(expected_case)
        observed_case['selected_slot'] = oracle.uc.mem_read(s['row']+0x9a69, 1)[0]
        observed_case['option_two'] = oracle.uc.mem_read(s['row']+0x9b25, 1)[0]
        observed_case['guard_9a01'] = int.from_bytes(oracle.uc.mem_read(s['row']+0x9a01, 4), 'little')
        observed_case['ordered_writes'] = copy.deepcopy(result['ordered_writes'])
        verify_case(observed_case, expected_case)
        return observed_case

    for kind, value in SEQUENCE:
        cases.append(execute(kind, value))
    checkpoint = oracle.capture_state()
    checkpoint_values = selected, option
    suffix = [('option', 1), ('lookup', 1), ('select', 0), ('option', 0), ('lookup', 1), ('lookup', 0)]
    first = [execute(k, v) for k, v in suffix]
    final = oracle.capture_state()
    oracle.restore_state(checkpoint)
    selected, option = checkpoint_values
    second = [execute(k, v) for k, v in suffix]
    require(first == second and oracle.capture_state() == final, 'continuation differs')
    oracle.full_state({0x9a69: selected, 0x9b25: option})
    successful_calls = copy.deepcopy(oracle.calls)
    successful_starts = sorted(oracle.starts)
    probes = []
    for label, args in [('null_club', [0, 0]), ('unsupported_slot', [s['club'], 2])]:
        oracle.restore_state(checkpoint)
        try:
            oracle.call(0x896660, args, s['context'])
            outcome = {'execution_status': 'returned', 'comparison_verdict': 'not_comparable'}
        except Censored as error:
            outcome = {'execution_status': 'censored', 'comparison_verdict': 'not_comparable',
                       'diagnostic': error.diagnostic}
        probes.append({'probe': label, **outcome, 'ordered_partial_writes': copy.deepcopy(oracle.writes)})
    oracle.restore_state(checkpoint)
    all_cases = cases+first
    registry_cases = [c for c in all_cases if c['kind'] == 'lookup' and c['location']['kind'] == 'human_registry']
    fallback_cases = [c for c in all_cases if c['branch'] == 'ordinary_fallback']
    all_writes = [w for c in all_cases for w in c['ordered_writes']]
    controls = {}

    def detect(name, candidates, mutate):
        detected = 0
        for original in candidates:
            candidate = copy.deepcopy(original)
            mutate(candidate)
            require(candidate != original, 'defect did not mutate observation')
            try:
                verify_case(candidate, original)
            except ValueError:
                detected += 1
        require(detected == len(candidates), 'undetected candidate defect')
        controls[name] = detected if candidates else None

    def change_write(c, field, value):
        c['ordered_writes'][0][field] = value

    writable = [c for c in all_cases if c['ordered_writes']]
    detect('wrong_human_stride', [c for c in registry_cases if c['value'] == 1],
           lambda c: c['location'].update(byte_offset=6371))
    detect('omitted_registry_write', registry_cases, lambda c: c.update(ordered_writes=[]))
    detect('elided_repeated_registry_write', [c for c in registry_cases if c['previous_slot'] == c['selected_slot']],
           lambda c: c.update(ordered_writes=[]))
    detect('word_instead_of_byte', writable, lambda c: change_write(c, 'width', 2))
    detect('wrong_registry_row', registry_cases, lambda c: c['location'].update(registry_index=0))
    detect('extra_rng_draw', all_cases, lambda c: c.update(rng_draws=1))
    detect('producer_changes_slot', [c for c in all_cases if c['kind'] == 'option'],
           lambda c: c.update(selected_slot=1-c['selected_slot']))
    detect('selector_changes_option', [c for c in all_cases if c['kind'] == 'select'],
           lambda c: c.update(option_two=1-c['option_two']))
    detect('immutable_guard_mutation', all_cases, lambda c: c.update(guard_9a01=1-c['guard_9a01']))
    detect('wrong_branch', registry_cases+fallback_cases,
           lambda c: c.update(branch='ordinary_fallback' if c['branch'] != 'ordinary_fallback' else 'registry_option_enabled'))
    detect('wrong_ordinary_index', fallback_cases, lambda c: c['location'].update(index=1))
    detect('fallback_mutates_selection', [c for c in fallback_cases if c['previous_slot'] != c['value']],
           lambda c: c.update(selected_slot=c['value']))
    detect('fallback_emits_write', fallback_cases, lambda c: c.update(ordered_writes=[{'registry_offset': 0x9a69, 'width': 1, 'value': c['value']}]))
    detect('ignore_option', fallback_cases if guard else [], lambda c: c.update(branch='registry_option_enabled'))
    detect('ignore_zero_guard', [c for c in registry_cases if c['option_two'] == 0] if not guard else [],
           lambda c: c.update(branch='ordinary_fallback'))
    reversed_cases = copy.deepcopy(all_writes)
    reversed_cases[0], reversed_cases[1] = reversed_cases[1], reversed_cases[0]
    try:
        verify_case(reversed_cases, all_writes)
    except ValueError:
        controls['reordered_effects'] = 1
    require(controls.get('reordered_effects') == 1, 'reordered stream undetected')
    require(len(successful_calls) <= 60, 'campaign call budget exceeded')
    receipt = {'schema_version': 1, 'execution_status': 'completed', 'comparison_verdict': 'matched',
               'method': 'official connected entry-to-return instructions; no code patches or stubbed callees',
               'specimen_sha256': SPECIMEN, 'capture': identity, 'source': source,
               'tools': {'unicorn': '2.1.4', 'capstone': capstone.__version__},
               'qualifier_sha256': digest(Path(__file__).read_bytes()),
               'source_dependencies': {name: digest(Path(__file__).with_name(name).read_bytes()) for name in
                   ['qualify_human_registry.py', 'qualify_manager_bound_plan.py', 'qualify_fresh_human_registry.py', 'qualify_human_registry_producer.py']},
               'private_projection': {'sha256': digest(canonical(projected)), 'bytes': len(canonical(projected)), 'admission': 'pending_independent_review'},
               'ordinary_inputs': projected['ordinary'], 'initial_guard_option_slot': [guard, registry['option_two'], registry['human']['selected_slot']],
               'successful_calls': len(successful_calls), 'successful_instruction_starts': [f'{a:08x}' for a in successful_starts],
               'instruction_ranges': [{'start': f'{a:08x}', 'end_exclusive': f'{b:08x}', 'sha256': digest(bytes(oracle.uc.mem_read(a, b-a)))} for a, b in RANGES],
               'calls': successful_calls, 'cases': cases, 'continuation_cases': first,
               'complete_captured_regions_and_image_checked_after_every_step': True,
               'checkpoint_continuation': 'complete_captured_memory_and_ordered_results_equal',
               'defect_controls_detected_cases': controls, 'unsupported_probes': probes,
               'limitations': ['Only exact initialized real bindings; no lifecycle or original UI/process/save claim',
                               'Real ordinary fallback is first bank slot zero only; second bank branch unqualified',
                               'Fresh is complete declared sparse regions, not complete runtime heap',
                               'Input consumption and Bosman/original process parity are separate gates']}
    return receipt, projected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary', type=Path); p.add_argument('capture', type=Path)
    p.add_argument('output', type=Path); p.add_argument('--source', choices=['retained', 'fresh'], required=True)
    p.add_argument('--build-receipt', type=Path); p.add_argument('--private-fixture', type=Path)
    a = p.parse_args()
    require(not a.output.exists() and (a.private_fixture is None or not a.private_fixture.exists()), 'output exists')
    try:
        receipt, projected = generate(a.binary, a.capture, a.source, a.build_receipt)
    except Exception as error:
        failure = {'execution_status': 'failed', 'comparison_verdict': 'not_comparable',
                   'exception_type': type(error).__name__, 'qualifier_sha256': digest(Path(__file__).read_bytes())}
        if ACTIVE_ORACLE is not None:
            failure['last_instruction'] = f'{ACTIVE_ORACLE.pc:08x}' if ACTIVE_ORACLE.pc else None
            failure['decoded'] = ACTIVE_ORACLE.decoded
            failure['ordered_partial_writes'] = copy.deepcopy(ACTIVE_ORACLE.writes)
            failure['ordered_partial_reads'] = copy.deepcopy(ACTIVE_ORACLE.ordered_reads)
        if isinstance(error, Censored):
            failure['diagnostic'] = error.diagnostic
            failure['ordered_partial_writes'] = error.partial_writes
        with a.output.open('x') as out:
            out.write(json.dumps(failure, indent=2)+'\n')
        raise SystemExit('failed; sanitized attempt retained') from None
    with a.output.open('x') as out:
        out.write(json.dumps(receipt, indent=2)+'\n')
    if a.private_fixture:
        fd = os.open(a.private_fixture, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as out:
            out.write(canonical(projected))
    print(json.dumps({'successful_calls': receipt['successful_calls'], 'receipt_sha256': digest(a.output.read_bytes()),
                      'projection_sha256': receipt['private_projection']['sha256']}))


if __name__ == '__main__':
    main()
