#!/usr/bin/env python3
"""Produce a private, retained-only two-member projection; never self-admit it.

Standard-library raw parsing only. No original execution, names or raw pointers
are emitted. The output is a new bounded fixture, not a complete squad or save.
"""
import argparse
import hashlib
import json
import os
import struct
from pathlib import Path
from pc_r10_projection_inventory import Memory, load, require, digest

SPECIMEN = '0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86'
CAPTURE = '302921d53add894761acb6ef425d930f8b83ff0a344efdf61c45fa94d1f5cfa8'
BACKEND = '144ed82c248228c7769c6785899527eae5b33c3d'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def project(memory):
    clubs, nations, staff, players = [memory.u32(a) for a in
                                    (0xae235c, 0xae2350, 0xae2364, 0xae236c)]
    require(0 < 2*nations < clubs <= 10000 and 16 < staff <= 100000 and
            0 < players <= 100000, 'dimensions')
    cb, sb, pb, context = [memory.u32(a) for a in
                          (0xae23b4, 0xae23bc, 0xae23c4, 0xde1d08)]
    memory.read(cb, clubs*581)
    memory.read(sb, staff*110)
    player_table = memory.read(pb, players*70)
    require(all(memory.i32(pb+70*i) == i for i in range(players)), 'player IDs')
    memory.read(context, 0x605)
    mapping = memory.u32(context+0x601)
    memory.read(mapping, (clubs+32)*145)
    matches = []
    for cid in range(clubs-2*nations):
        club = cb+cid*581
        require(memory.i32(club) == cid, 'club ID')
        manager = memory.u32(club+0xcf)
        if sb <= manager < sb+staff*110 and (manager-sb) % 110 == 0:
            mid = (manager-sb)//110
            if mid >= staff-16:
                require(memory.i32(manager) == mid and
                        memory.u32(manager+0x39) == club, 'manager reciprocal binding')
                matches.append((cid, club, mid))
    require(len(matches) == 1, 'unique ordinary human binding')
    cid, club, mid = matches[0]
    cache = memory.read(context+0x5f0, 1)[0]
    row = memory.read(mapping+145*cid, 145)
    words = [struct.unpack_from('<i', row, 2+4*i)[0] for i in range(20)]
    require(cache == 0 and words == [-1]*20, 'initial command domain')
    selected, invalid, mismatched, seen = [], 0, 0, set()
    for i in range(50):
        pointer = memory.u32(club+0xd7+4*i)
        require(pointer not in seen, 'duplicate member link')
        seen.add(pointer)
        if not (sb <= pointer < sb+staff*110 and (pointer-sb) % 110 == 0):
            invalid += 1
            continue
        sid = (pointer-sb)//110
        require(memory.i32(pointer) == sid, 'staff ID')
        link = memory.u32(pointer+0x61)
        require(pb <= link < pb+players*70 and (link-pb) % 70 == 0, 'player extent')
        require(memory.i32(link) == (link-pb)//70, 'player identity')
        if memory.u32(pointer+0x39) != club:
            mismatched += 1
            continue
        selected.append((sid, pointer, link))
    require(len(selected) == 43 and invalid == 2 and mismatched == 5, 'retained anomalies')
    selected.sort()
    chosen = selected[:2]
    fixture = dict(schema_version=1, origin='captured-bosman-two-member-assignment',
                   specimen_sha256=SPECIMEN, source_capture_sha256=CAPTURE,
                   image_sha256=digest(memory.ranges[0][1]),
                   heap_sha256=digest(memory.ranges[1][1]), backend_revision=BACKEND,
                   club_id=cid, manager_staff_id=mid, members=[s for s, _, _ in chosen],
                   row_mode=0, cache_count=cache, mapping=words)
    audit = dict(kind='bounded-assignment-projection-producer-v1', decision='not-self-admitted',
                 fixture_sha256=digest(canonical(fixture)), aligned_members=48,
                 invalid_links=invalid, association_mismatches=mismatched,
                 reciprocal_candidates=len(selected), player_table_sha256=digest(player_table),
                 selected_records=[dict(staff_sha256=digest(memory.read(p, 110)),
                                        player_sha256=digest(memory.read(q, 70)))
                                   for _, p, q in chosen],
                 mapping_row_sha256=digest(row))
    return fixture, audit


def exclusive(path, raw):
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('output_directory', type=Path)
    args = parser.parse_args()
    # Existing output directories are rejected; no prior attempt can be replaced.
    args.output_directory.mkdir(mode=0o700)
    fixture, audit = project(Memory(load(args.capture, 'retained')))
    exclusive(args.output_directory/'fixture.json', canonical(fixture))
    exclusive(args.output_directory/'producer-audit.json', canonical(audit)+b'\n')
    print(json.dumps({'kind': audit['kind'], 'fixture_sha256': audit['fixture_sha256'],
                      'decision': audit['decision']}))


if __name__ == '__main__':
    main()
