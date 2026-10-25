#!/usr/bin/env python3
"""Recover a PRIVATE three-club fixture from a pinned retained Bosman capture.

Never writes into source inputs. Outputs include private game names and belong
outside the repository. Public receipt contains only identities and structure.
This is host research glue, not a saved-game importer or production rule engine.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

SPECIMEN = '0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86'
CLEAN = '920cbf75653473d276cd33fbbe7a90553dcd6fff4c0878e848aaca7736dddac6'
PINS = {
    'snapshot/image.bin': (10383360, 'ae11ce3ef6267ad55be6aa6387f676704b1bb8a6310507db6c5ccfe494d45c3a'),
    'snapshot/heap.bin': (108564672, '30ee2baefad8f57f8760f30abc076586f2d13339bb1629f75346a5dcbc1357a0'),
    'receipt.json': (1835, '3220ab1283509aab773259e7a2e090765b8c4e4b09ba68620f2b93330c024214'),
    'cm0102_audit': (47615536, 'd083b6bb79a29692cd2c359a3eea7410bb995368eb4aff4d39c35a6b20d59ef0'),
    'probe.o': (5752, '9316cd15c6059724d02961b625994707a2f2b6b4bb133808a07d7722af437245'),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_file(path, size, expected):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        raise ValueError('source type or length mismatch')
    data = path.read_bytes()
    if len(data) != size or digest(data) != expected:
        raise ValueError('source identity mismatch')
    return data


class Memory:
    def __init__(self, image, heap):
        self.regions = [(0x400000, image), (0x70000000, heap)]

    def read(self, address, size):
        if not 0 <= address <= 0xffffffff or not 0 <= size <= 108564672:
            raise ValueError('invalid memory range')
        for base, data in self.regions:
            if base <= address and address + size <= base + len(data):
                return data[address-base:address-base+size]
        raise ValueError('unmapped memory range')

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def name(self, address, size):
        raw = self.read(address, size)
        if b'\0' not in raw:
            raise ValueError('unterminated name')
        result = raw.split(b'\0', 1)[0].decode('cp1252')
        if any(ord(c) < 32 or ord(c) == 127 for c in result):
            raise ValueError('control character in name')
        return result


def recover(capture, clean_tree, manifest):
    manifest_bytes = checked_file(manifest, 72879, CLEAN)
    clean_rows = []
    for line in manifest_bytes.decode('utf-8').splitlines():
        if line.startswith('#'):
            continue
        expected, size, relative = line.split('\t')
        parts = Path(relative).parts
        if Path(relative).is_absolute() or '..' in parts or '\\' in relative:
            raise ValueError('unsafe clean path')
        checked_file(clean_tree / relative, int(size), expected)
        clean_rows.append(relative)
    if len(clean_rows) != 760 or len(set(clean_rows)) != 760:
        raise ValueError('wrong clean manifest cardinality')
    data = {name: checked_file(capture / name, size, sha) for name, (size, sha) in PINS.items()}
    source_identity = {name: {'bytes': size, 'sha256': sha} for name, (size, sha) in PINS.items()}
    source_sha = digest(canonical(source_identity))
    provenance = json.loads(data['receipt.json'])
    if (provenance['specimen_sha256'] != SPECIMEN or
            provenance['upstream_commit'] != 'f9583098d39c77ac6982a5aa9daec56d74454531' or
            provenance['binary_sha256'] != PINS['cm0102_audit'][1] or
            not provenance['capture_only'] or provenance['exit_code'] != 0):
        raise ValueError('capture provenance mismatch')
    m = Memory(data['snapshot/image.bin'], data['snapshot/heap.bin'])
    club_count, staff_count = m.u32(0xae235c), m.u32(0xae2364)
    ordinary_limit = club_count - m.u32(0xae2350)
    context = m.u32(0xde1d08)
    first, first_count = m.u32(context+0x5f9), m.u32(context+0x5fd)
    second, second_count = m.u32(context+0x5f1), m.u32(context+0x5f5)
    mapping = m.u32(context+0x601)
    if (club_count, staff_count, ordinary_limit, first_count, second_count) != (2514, 9520, 2301, 17, 28):
        raise ValueError('captured layout counts mismatch')
    tactical = {
        'context': m.read(context, 0x605),
        'first_bank': m.read(first, first_count*6371),
        'second_bank': m.read(second, second_count*6371),
        'mapping': m.read(mapping, club_count*0x91),
    }
    clubs_base, staff_base = m.u32(0xae23b4), m.u32(0xae23bc)
    m.read(clubs_base, club_count*581)
    m.read(staff_base, staff_count*110)
    clubs, selected = [], []
    for club_id in range(ordinary_limit):
        club_address = clubs_base + club_id*581
        if m.u32(club_address) != club_id or club_id >= ordinary_limit:
            raise ValueError('club identity mismatch')
        manager = m.u32(club_address+0xcf)
        delta = manager-staff_base
        if delta < 0 or delta % 110 or delta//110 >= staff_count-16:
            continue
        manager_id = m.u32(manager)
        if manager_id != delta//110:
            raise ValueError('manager row identity mismatch')
        plan = struct.unpack('<h', m.read(mapping+club_id*0x91, 2))[0]
        if not 0 <= plan < first_count:
            continue
        names = [m.name(m.u32(manager+offset), 51) for offset in (4, 8)]
        club = {'id': club_id, 'name': m.name(club_address+4, 51),
                'manager_id': manager_id, 'manager_name': ' '.join(n for n in names if n),
                'selected_plan': plan}
        if not club['name'] or not club['manager_name']:
            raise ValueError('empty recovered name')
        clubs.append(club)
        selected.append({'club_address': club_address, 'club_id': club_id,
                         'manager_address': manager, 'manager_id': manager_id,
                         'club_record_sha256': digest(m.read(club_address, 581)),
                         'manager_record_sha256': digest(m.read(manager, 110))})
        if len(clubs) == 3:
            break
    if len(clubs) != 3:
        raise ValueError('insufficient eligible captured records')
    fixture = {'schema_version': 1, 'origin': 'captured-bosman', 'source_capture_sha256': source_sha,
               'specimen_sha256': SPECIMEN, 'club_count': club_count, 'staff_count': staff_count,
               'ordinary_club_limit': ordinary_limit, 'first_bank_count': first_count,
               'second_bank_count': second_count, 'clubs': clubs}
    fixture_bytes = canonical(fixture)
    public = {'schema_version': 1, 'source_capture_sha256': source_sha,
              'source_capture_identity_scheme': 'SHA256 of canonical capture_sources: sorted keys, UTF8, compact JSON; not a single raw-file hash',
              'specimen_sha256': SPECIMEN, 'capture_sources': source_identity,
              'bosman_source_revision': provenance['upstream_commit'],
              'clean_manifest_sha256': CLEAN, 'clean_files_verified': len(clean_rows),
              'fixture': {'schema_version': 1, 'bytes': len(fixture_bytes), 'sha256': digest(fixture_bytes),
                          'club_records': 3, 'manager_records': 3},
              'tactical_regions': {key: {'bytes': len(value), 'sha256': digest(value)} for key, value in tactical.items()},
              'counts': {key: fixture[key] for key in ('club_count', 'staff_count', 'ordinary_club_limit', 'first_bank_count', 'second_bank_count')},
              'results': {'manager_pointers_in_staff_table': True, 'manager_ids_below_reserved_threshold': True,
                          'club_ids_in_ordinary_range': True, 'existing_selections_in_first_bank': True},
              'scope': 'Retained instrumented older Bosman runtime; clean source tree rehashed now; no original-process observation or new replay.'}
    private = {'source_capture_sha256': source_sha, 'context_address': context, 'mapping_address': mapping,
               'first_bank_address': first, 'second_bank_address': second, 'clubs': selected}
    return fixture_bytes, canonical(public), canonical(private)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--clean-tree', type=Path, required=True)
    parser.add_argument('--clean-manifest', type=Path, required=True)
    parser.add_argument('--private-output', type=Path, required=True)
    parser.add_argument('--public-receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.private_output.exists() or args.public_receipt.exists():
        raise ValueError('output already exists')
    fixture, receipt, private = recover(args.capture, args.clean_tree, args.clean_manifest)
    args.private_output.mkdir(mode=0o700, parents=False)
    for name, content in [('fixture.json', fixture), ('selected.json', private)]:
        path = args.private_output / name
        with path.open('xb') as out:
            out.write(content)
        path.chmod(0o600)
    with args.public_receipt.open('xb') as out:
        out.write(receipt+b'\n')
    print(json.dumps({'fixture_sha256': digest(fixture), 'fixture_bytes': len(fixture)}))


if __name__ == '__main__':
    main()
