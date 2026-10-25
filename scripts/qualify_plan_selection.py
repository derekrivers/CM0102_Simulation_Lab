#!/usr/bin/env python3
"""Bounded original-instruction oracle. Never starts a Windows process.

Research: Derek Rivers, Reversal MIT, pin 9b0d1a5, tactics-boundary-10.
Requires Unicorn 2.1.4. Inputs stay private; output contains synthetic state.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import unicorn
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

SPECIMEN = '0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86'
RANGES = [(0x8967d0, 0x8968e6), (0x8982b0, 0x8983f0), (0x600a50, 0x600c90), (0x5409b0, 0x540a4c)]
CTX, CLUB, ROWS, STACK, STOP = 0x1000000, 0x1010000, 0x1020000, 0x2000000, 0x3000000


def generate(binary):
    raw = binary.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SPECIMEN:
        raise ValueError('specimen mismatch')
    if unicorn.__version__ != '2.1.4':
        raise ValueError('requires Unicorn 2.1.4')
    pe = struct.unpack_from('<I', raw, 0x3c)[0]
    opt = pe + 24
    if struct.unpack_from('<H', raw, opt)[0] != 0x10b:
        raise ValueError('requires PE32')
    base = struct.unpack_from('<I', raw, opt + 28)[0]
    image_size = struct.unpack_from('<I', raw, opt + 56)[0]
    header = struct.unpack_from('<I', raw, opt + 60)[0]
    count = struct.unpack_from('<H', raw, pe + 6)[0]
    optsize = struct.unpack_from('<H', raw, pe + 20)[0]
    uc = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
    uc.mem_map(base, (image_size + 4095) & ~4095)
    uc.mem_write(base, raw[:header])
    for n in range(count):
        _, rva, size, offset = struct.unpack_from('<IIII', raw, opt + optsize + 40*n + 8)
        uc.mem_write(base+rva, raw[offset:offset+size])
    for address in [CTX, CLUB, ROWS, STACK, STOP]:
        uc.mem_map(address, 0x10000)
    starts, effects = set(), []

    def instruction(machine, address, size, unused):
        if not any(a <= address and address+size <= b for a, b in RANGES):
            raise ValueError(f'outside admitted code: {address:x}')
        starts.add(address)

    def write(machine, access, address, size, value, unused):
        if STACK <= address < STACK+0x10000:
            return
        if not ROWS <= address or address+size > ROWS+4*0x91:
            raise ValueError('unexpected non-stack write')
        effects.append({'offset': address-ROWS, 'width': size, 'value': value})

    uc.hook_add(unicorn.UC_HOOK_CODE, instruction)
    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
    context = bytearray(0x1000)
    struct.pack_into('<I', context, 0x5fd, 3)
    struct.pack_into('<I', context, 0x5f5, 2)
    struct.pack_into('<I', context, 0x601, ROWS)
    uc.mem_write(CTX, bytes(context))
    # Classifier fallback: club ID < (club count - alternate count).
    uc.mem_write(0xae235c, struct.pack('<I', 4))
    uc.mem_write(0xae2350, struct.pack('<I', 0))
    cases = []
    # Independent cases plus a connected stream; upper bits test the original ABI.
    schedule = [(c, p) for c in range(4) for p in range(5)] + [(2, 4), (2, 4), (0, 1), (3, 0x12340003)]
    mapping = bytearray([0xa5]* (4*0x91))
    for club, arg in schedule:
        before = bytes(mapping)
        uc.mem_write(ROWS, before)
        club_data = bytearray(0x1000)
        struct.pack_into('<I', club_data, 0, club)
        uc.mem_write(CLUB, bytes(club_data))
        sp = STACK+0x8000
        uc.mem_write(sp, struct.pack('<IIII', STOP, CLUB, arg, 0))
        uc.reg_write(UC_X86_REG_ESP, sp)
        uc.reg_write(UC_X86_REG_ECX, CTX)
        effects.clear()
        uc.emu_start(0x8967d0, STOP, timeout=100000, count=1000)
        if uc.reg_read(UC_X86_REG_EIP) != STOP or uc.reg_read(UC_X86_REG_ESP) != sp+16:
            raise ValueError('return ABI mismatch')
        after = bytes(uc.mem_read(ROWS, len(mapping)))
        expected = bytearray(before)
        struct.pack_into('<H', expected, club*0x91, arg & 0xffff)
        expected_effects = [{'offset': club*0x91, 'width': 2, 'value': arg & 0xffff}]
        if (after != expected or effects != expected_effects or uc.reg_read(UC_X86_REG_EAX) != 1
                or bytes(uc.mem_read(CTX, len(context))) != context
                or bytes(uc.mem_read(CLUB, len(club_data))) != club_data):
            raise ValueError('unexpected effects/result')
        cases.append({'club_id': club, 'abi_plan_argument': arg, 'selected_plan': arg & 0xffff,
                      'before_sha256': hashlib.sha256(before).hexdigest(),
                      'after_sha256': hashlib.sha256(after).hexdigest(),
                      'ordered_writes': list(effects), 'return': 1})
        mapping[:] = after
    # Prove corpus discriminates four implementation defects.
    negative = {}
    for name in ['wrong-row', 'dword-store', 'extra-write', 'omitted-write']:
        detected = 0
        for case in cases:
            writes = case['ordered_writes']
            changed = [dict(w) for w in writes]
            if name == 'wrong-row': changed[0]['offset'] += 0x91
            if name == 'dword-store': changed[0]['width'] = 4
            if name == 'extra-write': changed += [{'offset': 4, 'width': 1, 'value': 0}]
            if name == 'omitted-write': changed = []
            detected += changed != writes
        if detected != len(cases):
            raise ValueError('ineffective negative control')
        negative[name] = detected
    return {'schema_version': 1, 'specimen_sha256': SPECIMEN,
            'research_revision': '9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345',
            'method': 'original entry-to-return instructions; no stubbed callees; synthetic preinitialized null-owner clubs; option zero',
            'emulator': 'unicorn '+unicorn.__version__,
            'instruction_ranges': [{'va_start': hex(a), 'va_end_exclusive': hex(b),
                                    'sha256': hashlib.sha256(bytes(uc.mem_read(a,b-a))).hexdigest()} for a,b in RANGES],
            'executed_instruction_starts': len(starts), 'cases': cases, 'negative_controls': negative,
            'limitations': ['No original UI command binding, tactical plan contents, human registry, diagnostics, squad capture or save compatibility',
                            'Invalid actions rejected by Rust preflight; original diagnostic paths are not equivalent']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    data = generate(args.binary)
    with args.output.open('x', encoding='utf-8') as out:
        out.write(json.dumps(data, indent=2)+'\n')
    print(json.dumps({'cases': len(data['cases']), 'starts': data['executed_instruction_starts'],
                      'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}))
