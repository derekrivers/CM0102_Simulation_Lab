#!/usr/bin/env python3
"""Independent read-only R10 raw inventory; never qualifies or admits a squad.

Only Python standard library. No producer/oracle parser imports. Output contains
aggregate structure and hashes, never names, native pointers or record IDs.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

PINS = {
    'image.bin': 'ae11ce3ef6267ad55be6aa6387f676704b1bb8a6310507db6c5ccfe494d45c3a',
    'heap.bin': '30ee2baefad8f57f8760f30abc076586f2d13339bb1629f75346a5dcbc1357a0',
}
SPARSE = '014808018f7b20f60abaac5c71a0c509747259e309563650afe0d0cc79da6f40'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def read_file(path, cap, expected):
    require(path.is_file() and not path.is_symlink(), 'regular input required')
    require(path.stat().st_size <= cap, 'input cap')
    raw = path.read_bytes()
    require(len(raw) <= cap and digest(raw) == expected, 'input identity')
    return raw


def load(path, kind):
    if kind == 'retained':
        return [(0x400000, read_file(path/'image.bin', 32*1024**2, PINS['image.bin'])),
                (0x70000000, read_file(path/'heap.bin', 256*1024**2, PINS['heap.bin']))]
    raw = read_file(path, 16778000, SPARSE)
    require(raw[:8] == b'PCR5SP01' and raw[-8:] == b'PCR5DONE', 'sparse envelope')
    ranges, cursor = [], 8
    while cursor < len(raw)-8:
        require(cursor+8 <= len(raw)-8, 'sparse header')
        address, size = struct.unpack_from('<II', raw, cursor)
        cursor += 8
        require(0 < size <= 8388608 and address+size <= 2**32 and
                cursor+size <= len(raw)-8, 'sparse extent')
        ranges.append((address, raw[cursor:cursor+size]))
        cursor += size
    require(cursor == len(raw)-8 and len(ranges) == 16, 'sparse completion')
    return ranges


class Memory:
    def __init__(self, ranges):
        ordered = sorted(ranges)
        for index, (base, raw) in enumerate(ordered):
            require(0 <= base < base+len(raw) <= 2**32, 'range extent')
            if index:
                prior, data = ordered[index-1]
                require(prior+len(data) <= base, 'overlap')
        self.ranges = ordered

    def read(self, address, size):
        require(0 <= address <= address+size <= 2**32, 'read extent')
        for base, raw in self.ranges:
            if base <= address and address+size <= base+len(raw):
                return raw[address-base:address-base+size]
        raise ValueError('missing captured extent')

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def i32(self, address):
        return struct.unpack('<i', self.read(address, 4))[0]


def inventory(memory):
    clubs, nations, staff = [memory.u32(a) for a in (0xae235c, 0xae2350, 0xae2364)]
    require(0 < 2*nations < clubs <= 10000 and 16 < staff <= 100000, 'dimensions')
    cb, sb, context = [memory.u32(a) for a in (0xae23b4, 0xae23bc, 0xde1d08)]
    club_bytes, staff_bytes = memory.read(cb, clubs*581), memory.read(sb, staff*110)
    memory.read(context, 0x605)
    mapping = memory.u32(context+0x601)
    mapping_bytes = memory.read(mapping, (clubs+32)*145)
    matches = []
    for index in range(clubs-2*nations):
        club = cb+index*581
        require(memory.i32(club) == index, 'club table ID')
        manager = memory.u32(club+0xcf)
        if sb <= manager < sb+staff*110 and (manager-sb) % 110 == 0:
            mid = (manager-sb)//110
            if mid >= staff-16:
                require(memory.i32(manager) == mid and memory.u32(manager+0x39) == club,
                        'human reciprocal binding')
                matches.append((index, club))
    require(len(matches) == 1, 'unique human binding')
    index, club = matches[0]
    counts = dict(null=0, nonnull=0, duplicate_pointer=0, outside_or_unaligned=0, minus_one_pointer=0,
                  id_mismatch=0, club_link_mismatch=0, player_link_null=0,
                  player_link_first_byte_captured=0, reciprocal_player_candidates=0)
    seen = set()
    for slot in range(50):
        pointer = memory.u32(club+0xd7+4*slot)
        if not pointer:
            counts['null'] += 1
            continue
        counts['nonnull'] += 1
        counts['minus_one_pointer'] += pointer == 0xffffffff
        counts['duplicate_pointer'] += pointer in seen
        seen.add(pointer)
        if not (sb <= pointer < sb+staff*110 and (pointer-sb) % 110 == 0):
            counts['outside_or_unaligned'] += 1
            continue
        sid = (pointer-sb)//110
        id_ok = memory.i32(pointer) == sid
        reciprocal = memory.u32(pointer+0x39) == club
        player = memory.u32(pointer+0x61)
        counts['id_mismatch'] += not id_ok
        counts['club_link_mismatch'] += not reciprocal
        counts['player_link_null'] += not player
        if player:
            try:
                memory.read(player, 1)
                counts['player_link_first_byte_captured'] += 1
            except ValueError:
                pass
        counts['reciprocal_player_candidates'] += bool(id_ok and reciprocal and player)
    words = [memory.i32(mapping+145*index+2+4*i) for i in range(20)]
    return {'status': 'inventory-only-not-admitted', 'counts': counts,
            'mapping': {'slots': 20, 'empty_minus_one': words.count(-1),
                        'other_negative': sum(value < -1 for value in words),
                        'nonnull_id_outside_staff': sum(value >= staff for value in words)},
            'hashes': {'club_table': digest(club_bytes), 'staff_table': digest(staff_bytes),
                       'mapping_table': digest(mapping_bytes),
                       'human_club_record': digest(memory.read(club, 581)),
                       'human_mapping_row': digest(memory.read(mapping+145*index, 145))},
            'limitations': ['Candidate member layout, not qualified squad semantics',
                           'Pointer nonnull/first-byte coverage is not player object extent or lifetime',
                           'No real projection produced and no fingerprint admitted']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['retained', 'fresh'])
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    ranges = load(args.input, args.kind)
    result = inventory(Memory(ranges))
    result['source'] = {'kind': args.kind, 'pins': PINS if args.kind == 'retained' else {'capture': SPARSE}}
    with args.output.open('x', encoding='utf8') as output:
        output.write(json.dumps(result, indent=2, sort_keys=True)+'\n')
    args.output.chmod(0o600)
    print(json.dumps({'status': result['status'], 'output_sha256': digest(args.output.read_bytes()),
                      'counts': result['counts'], 'mapping': result['mapping']}, sort_keys=True))
