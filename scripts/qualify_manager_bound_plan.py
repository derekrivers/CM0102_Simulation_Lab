#!/usr/bin/env python3
"""Replay manager-bound tactical selection against an immutable private runtime capture.

No Windows process is launched. Public output is hashes, structural metadata and
normalized effects only; raw game records and tactical banks remain private.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import unicorn
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

SPECIMEN = '0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86'
IMAGE_HASH = 'ae11ce3ef6267ad55be6aa6387f676704b1bb8a6310507db6c5ccfe494d45c3a'
HEAP_HASH = '30ee2baefad8f57f8760f30abc076586f2d13339bb1629f75346a5dcbc1357a0'
IMAGE_BASE, HEAP_BASE = 0x400000, 0x70000000
STACK, STOP = 0x20000000, 0x21000000
RANGES = [(0x896660, 0x8967c1), (0x8967d0, 0x8968e6),
          (0x8982b0, 0x8983ed), (0x600a50, 0x600c88), (0x5409b0, 0x540a4c)]
GLOBALS = [0xde1d08, 0xae235c, 0xae2350, 0xae2364, 0xae23b4, 0xae23bc]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(path, expected):
    data = path.read_bytes()
    if digest(data) != expected:
        raise ValueError('input identity mismatch: ' + path.name)
    return data


class Snapshot:
    def __init__(self, directory):
        self.image = checked(directory / 'image.bin', IMAGE_HASH)
        self.heap = checked(directory / 'heap.bin', HEAP_HASH)

    def read(self, address, size):
        for base, data in [(IMAGE_BASE, self.image), (HEAP_BASE, self.heap)]:
            offset = address - base
            if 0 <= offset and offset + size <= len(data):
                return data[offset:offset + size]
        raise ValueError('pointer extent outside captured memory')

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def s32(self, address):
        return struct.unpack('<i', self.read(address, 4))[0]

    def s16(self, address):
        return struct.unpack('<h', self.read(address, 2))[0]


def generate(binary, capture):
    if unicorn.__version__ != '2.1.4':
        raise ValueError('requires Unicorn 2.1.4')
    raw = checked(binary, SPECIMEN)
    snapshot = Snapshot(capture)
    pe = struct.unpack_from('<I', raw, 0x3c)[0]
    opt = pe + 24
    if raw[:2] != b'MZ' or raw[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', raw, opt)[0] != 0x10b:
        raise ValueError('requires PE32')
    base = struct.unpack_from('<I', raw, opt + 28)[0]
    image_size = struct.unpack_from('<I', raw, opt + 56)[0]
    if base != IMAGE_BASE:
        raise ValueError('image base mismatch')
    uc = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
    uc.mem_map(base, (image_size + 4095) & ~4095)
    header = struct.unpack_from('<I', raw, opt + 60)[0]
    uc.mem_write(base, raw[:header])
    count = struct.unpack_from('<H', raw, pe + 6)[0]
    optsize = struct.unpack_from('<H', raw, pe + 20)[0]
    for index in range(count):
        _, rva, size, offset = struct.unpack_from('<IIII', raw, opt + optsize + 40*index + 8)
        uc.mem_write(base+rva, raw[offset:offset+size])
    uc.mem_map(HEAP_BASE, (len(snapshot.heap) + 4095) & ~4095)
    uc.mem_write(HEAP_BASE, snapshot.heap)
    uc.mem_map(STACK, 0x10000)
    uc.mem_map(STOP, 0x1000)
    # Only admitted global data is transplanted. Every executed code byte comes
    # from the hash-verified official PE, never from Bosman's runtime image.
    for address in GLOBALS:
        uc.mem_write(address, snapshot.read(address, 4))
    context = snapshot.u32(0xde1d08)
    clubs, nations, staff = [snapshot.u32(a) for a in GLOBALS[1:4]]
    club_base, staff_base = [snapshot.u32(a) for a in GLOBALS[4:]]
    first, second = snapshot.s32(context+0x5fd), snapshot.s32(context+0x5f5)
    bank1, bank2, rows = [snapshot.u32(context+a) for a in [0x5f9, 0x5f1, 0x601]]
    if not 0 < nations*2 < clubs or not 16 < staff or not 0 < first < 32768 or not 0 < second < 32768-first:
        raise ValueError('unsupported counts')
    snapshot.read(club_base, clubs*581)
    snapshot.read(staff_base, staff*110)
    snapshot.read(rows, clubs*0x91)
    banks = [snapshot.read(bank1, first*6371), snapshot.read(bank2, second*6371)]
    selected = []
    for index in range(clubs-nations):
        club = club_base + index*581
        manager = snapshot.u32(club+0xcf)
        if manager == 0 or not staff_base <= manager < staff_base+staff*110 or (manager-staff_base) % 110:
            continue
        manager_id = snapshot.s32(manager)
        if snapshot.s32(club) != index or manager_id != (manager-staff_base)//110 or not 0 <= manager_id < staff-16:
            continue
        plan = snapshot.s16(rows+index*0x91)
        if not 0 <= plan < first+second:
            continue
        selected.append((club, manager, index, manager_id, plan))
        if len(selected) == 3:
            break
    if len(selected) != 3:
        raise ValueError('three supported actual manager-bound clubs required')
    starts, writes, reads = set(), [], set()
    current_row, read_ranges = 0, []

    def instruction(machine, address, size, unused):
        if not any(a <= address and address+size <= b for a, b in RANGES):
            raise ValueError(f'outside admitted original instructions: {address:x}')
        starts.add(address)

    def read(machine, access, address, size, value, unused):
        if STACK <= address and address+size <= STACK+0x10000:
            return
        if not any(a <= address and address+size <= b for a, b in read_ranges):
            raise ValueError(f'outside admitted state read: {address:x}/{size}')
        reads.add((address, size))

    def write(machine, access, address, size, value, unused):
        if STACK <= address and address+size <= STACK+0x10000:
            return
        if address != current_row or size != 2:
            raise ValueError('unexpected non-stack write')
        writes.append({'row_relative_offset': 0, 'width': size, 'value': value})

    uc.hook_add(unicorn.UC_HOOK_CODE, instruction)
    uc.hook_add(unicorn.UC_HOOK_MEM_READ, read)
    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)

    def call(entry, arguments, expected):
        sp = STACK+0x8000
        uc.mem_write(sp, struct.pack('<'+'I'*(len(arguments)+1), STOP, *arguments))
        uc.reg_write(UC_X86_REG_ESP, sp)
        uc.reg_write(UC_X86_REG_ECX, context)
        writes.clear()
        reads.clear()
        uc.emu_start(entry, STOP, timeout=100000, count=1000)
        if (uc.reg_read(UC_X86_REG_EIP) != STOP or
                uc.reg_read(UC_X86_REG_ESP) != sp+4*(1+len(arguments)) or
                uc.reg_read(UC_X86_REG_EAX) != expected):
            raise ValueError('entry-to-return output or ABI mismatch')
        return list(writes)

    cases, records = [], []
    for label, (club, manager, index, manager_id, captured_plan) in enumerate(selected):
        current_row = rows+index*0x91
        read_ranges = [(a,a+4) for a in GLOBALS] + [
            (club,club+4), (club+0xcf,club+0xd3), (manager,manager+4),
            (context+0x5f1,context+0x605), (current_row,current_row+2)]
        records.append({'label': label, 'club_record_sha256': digest(snapshot.read(club,581)),
                        'manager_record_sha256': digest(snapshot.read(manager,110)),
                        'mapping_record_sha256': digest(snapshot.read(current_row,0x91)),
                        'manager_pointer_nonnull': True, 'manager_id_matches_record_index': True,
                        'outside_human_reserved_ids': True, 'ordinary_club': True})
        # Include both banks' boundaries, captured state, repeated writes and
        # opaque nonzero options. The original low-word ABI is also exercised.
        plans = [captured_plan, 0, first-1, first, first+second-1, first, first]
        for step, plan in enumerate(plans):
            option = [0, 1, 0xffffffff][step % 3]
            argument = plan if step != 6 else 0x12340000 | plan
            before = bytes(uc.mem_read(current_row,0x91))
            effects = call(0x8967d0, [club, argument, option], 1)
            expected = bytearray(before)
            struct.pack_into('<H', expected, 0, plan)
            after = bytes(uc.mem_read(current_row,0x91))
            if after != expected or effects != [{'row_relative_offset': 0, 'width': 2, 'value': plan}]:
                raise ValueError('setter effect mismatch')
            if call(0x8982b0, [club, option], index):
                raise ValueError('row resolver wrote state')
            bank, bank_index = (0, plan) if plan < first else (1, plan-first)
            pointer = [bank1,bank2][bank]+bank_index*6371
            if call(0x896660, [club, option], pointer):
                raise ValueError('ordinary manager lookup wrote state')
            if bytes(uc.mem_read(pointer,6371)) != snapshot.read(pointer,6371):
                raise ValueError('selected plan bytes changed')
            cases.append({'club_label': label, 'step': step, 'plan_index': plan,
                          'abi_plan_argument': argument, 'opaque_option': option,
                          'setter_return': 1, 'setter_ordered_writes': effects,
                          'row_resolver_matches_club_id': True, 'lookup_bank': bank,
                          'lookup_bank_index': bank_index, 'lookup_byte_offset': bank_index*6371,
                          'lookup_ordered_writes': [],
                          'mapping_before_sha256': digest(before), 'mapping_after_sha256': digest(after),
                          'resolved_plan_sha256': digest(snapshot.read(pointer,6371))})
    # Compare the complete heap against the original capture with precisely
    # the admitted words changed; this checks all sentinels and both banks.
    expected_heap = bytearray(snapshot.heap)
    for club, manager, index, manager_id, captured_plan in selected:
        offset = rows+index*0x91-HEAP_BASE
        expected_heap[offset:offset+2] = uc.mem_read(rows+index*0x91,2)
    if bytes(uc.mem_read(HEAP_BASE,len(expected_heap))) != expected_heap:
        raise ValueError('unexpected captured-heap mutation')
    # Deliberately wrong normalized transition models, compared against actual
    # observed outputs. A zero-index pointer cannot discriminate stride errors.
    defects = {'wrong-row': 0, 'dword-store': 0, 'omitted-store': 0,
               'extra-registry-write': 0, 'wrong-bank': 0, 'wrong-stride': 0}
    for case in cases:
        observed = case['setter_ordered_writes']
        mutants = {
            'wrong-row': [{'row_relative_offset': 0x91, 'width': 2, 'value': case['plan_index']}],
            'dword-store': [{'row_relative_offset': 0, 'width': 4, 'value': case['plan_index']}],
            'omitted-store': [],
            'extra-registry-write': observed + [{'registry_offset': 0x9a69, 'width': 1, 'value': 0}],
        }
        for defect, mutant in mutants.items():
            defects[defect] += mutant != observed
        actual = [bank1,bank2][case['lookup_bank']] + case['lookup_bank_index']*6371
        wrong_bank = [bank2,bank1][case['lookup_bank']] + case['lookup_bank_index']*6371
        wrong_stride = [bank1,bank2][case['lookup_bank']] + case['lookup_bank_index']*6370
        defects['wrong-bank'] += actual != wrong_bank
        defects['wrong-stride'] += actual != wrong_stride
    if min(defects.values()) == 0:
        raise ValueError('non-discriminating corpus')
    # Negative probes execute original code only until it first exits the
    # qualified instruction boundary; they are censored, never passing returns.
    club, manager, index, manager_id, captured_plan = selected[-1]
    successful_starts = len(starts)
    boundary_probes = []
    for name, plan, manager_value in [
            ('negative-plan-enters-diagnostics', 0xffffffff, manager_id),
            ('limit-plan-enters-diagnostics', first+second, manager_id),
            ('human-reserved-id-enters-unqualified-classification', 0, staff-16)]:
        uc.mem_write(manager, struct.pack('<I', manager_value))
        try:
            call(0x8967d0, [club, plan, 0], 1)
        except ValueError as error:
            if not str(error).startswith('outside admitted original instructions:') or writes:
                raise
            boundary_probes.append({'name': name, 'execution_status': 'censored-at-boundary',
                                    'comparison_verdict': 'unsupported',
                                    'first_unadmitted_instruction': str(error).split(': ')[1],
                                    'nonstack_writes_before_boundary': []})
        else:
            raise ValueError('negative probe unexpectedly returned')
        finally:
            uc.mem_write(manager, struct.pack('<I', manager_id))
    # Host admission guards are structural tests, not original rejection claims.
    def admitted(club_id, manager_pointer, manager_record_id, selection):
        return (0 <= club_id < clubs-nations and manager_pointer != 0 and
                staff_base <= manager_pointer < staff_base+staff*110 and
                (manager_pointer-staff_base) % 110 == 0 and
                manager_record_id == (manager_pointer-staff_base)//110 and
                0 <= manager_record_id < staff-16 and 0 <= selection < first+second)
    guard_tests = [
        ('negative-club-id', -1, manager, manager_id, 0),
        ('national-club-id', clubs-nations, manager, manager_id, 0),
        ('null-manager', index, 0, manager_id, 0),
        ('outside-manager-table', index, staff_base-110, manager_id, 0),
        ('unaligned-manager', index, manager+1, manager_id, 0),
        ('mismatched-manager-id', index, manager, manager_id+1, 0),
        ('human-reserved-id', index, staff_base+(staff-16)*110, staff-16, 0),
        ('negative-selection', index, manager, manager_id, -1),
        ('limit-selection', index, manager, manager_id, first+second),
    ]
    if not admitted(index,manager,manager_id,0) or any(admitted(*test[1:]) for test in guard_tests):
        raise ValueError('ineffective input guard')
    return {'schema_version': 1, 'specimen_sha256': SPECIMEN,
            'method': 'official PE entry-to-return instructions over actual retained runtime heap; no stubbed callees',
            'emulator': 'unicorn '+unicorn.__version__,
            'capture': {'image_sha256': IMAGE_HASH, 'heap_sha256': HEAP_HASH,
                        'source_capture_sha256': '302921d53add894761acb6ef425d930f8b83ff0a344efdf61c45fa94d1f5cfa8',
                        'platform_revision': 'f9583098d39c77ac6982a5aa9daec56d74454531',
                        'qualification': 'historical instrumented Bosman capture; not current platform certification'},
            'counts': {'clubs': clubs, 'nations': nations, 'staff': staff, 'first_bank': first, 'second_bank': second},
            'bank_sha256': [digest(b) for b in banks], 'records': records,
            'instruction_ranges': [{'start': hex(a), 'end_exclusive': hex(b),
                                    'sha256': digest(bytes(uc.mem_read(a,b-a)))} for a,b in RANGES],
            'successful_instruction_starts': successful_starts,
            'executed_instruction_starts_including_censored_probes': len(starts), 'cases': cases,
            'defect_discrimination_case_counts': defects, 'boundary_probes': boundary_probes,
            'host_guard_rejections': [test[0] for test in guard_tests],
            'entire_heap_unchanged_except_selected_words': True,
            'limitations': ['AI manager-bound ordinary clubs only; human manager registry, national teams and diagnostics unqualified',
                            'Captured runtime state from historical Bosman instrumentation, replayed by official PE instructions',
                            'No live original-process capture, full loader, original UI binding, plan semantic decoding, match application or original save compatibility',
                            'The setter, row resolver and getter are connected API calls, not execution of their full match-setup caller']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = generate(args.binary, args.capture)
    with args.output.open('x', encoding='utf-8') as out:
        out.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'cases': len(result['cases']), 'starts': result['successful_instruction_starts'],
                      'sha256': digest(args.output.read_bytes())}))
