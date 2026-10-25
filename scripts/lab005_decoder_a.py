"""LAB-005 decoder A: address reads and integer arithmetic; no parser imports."""
import hashlib


class DecodeBoundary(ValueError):
    def __init__(self, reason, dimensions=None):
        super().__init__(reason)
        self.dimensions = dimensions


def decode(regions):
    for i, (base, raw) in enumerate(regions):
        if not 0 <= base < base+len(raw) <= 2**32 or any(
                base < other+len(data) and other < base+len(raw)
                for other, data in regions[:i]):
            raise DecodeBoundary('invalid-or-overlapping-regions')
    def read(address, width):
        for base, raw in regions:
            if base <= address and address + width <= base + len(raw):
                return raw[address-base:address-base+width]
        return None

    def integer(address, signed=False):
        raw = read(address, 4)
        return None if raw is None else int.from_bytes(raw, 'little', signed=signed)

    values = [integer(a) for a in (0xae235c, 0xae2350, 0xae2364,
                                   0xae236c, 0xae23b4, 0xae23bc, 0xae23c4)]
    if None in values:
        raise DecodeBoundary('missing-globals')
    nc, nn, ns, np, cb, sb, pb = values
    if not (0 < 2*nn < nc <= 10000 and 16 < ns <= 100000 and 0 < np <= 100000):
        raise DecodeBoundary('dimensions')
    dimensions = dict(clubs=nc, nations=nn, staff=ns, players=np)
    bindings = []
    for i in range(nc-2*nn):
        club = cb+i*581
        manager = integer(club+0xcf)
        if manager is None:
            raise DecodeBoundary('incomplete-binding-search', dimensions)
        if sb <= manager < sb+ns*110 and (manager-sb) % 110 == 0:
            mid = (manager-sb)//110
            if mid >= ns-16:
                fields = [integer(manager, True), integer(club, True), integer(manager+0x39)]
                if None in fields:
                    raise DecodeBoundary('incomplete-binding-search', dimensions)
                if fields == [mid, i, club]:
                    bindings.append(club)
    if len(bindings) != 1:
        raise DecodeBoundary('unique-binding-unavailable', dimensions)
    club = bindings[0]

    def record(pointer):
        item = dict(pointer=pointer, staff_index=None, staff_id=None,
                    club_pointer=None, player_pointer=None, player_index=None,
                    player_id=None, staff_sha256=None, player_sha256=None)
        flags = []
        if pointer is None:
            flags.append('missing-slot')
        elif not sb <= pointer < sb+ns*110:
            flags.append('outside-staff')
        elif (pointer-sb) % 110:
            flags.append('unaligned-staff')
        else:
            index = (pointer-sb)//110
            item['staff_index'] = index
            raw = read(pointer, 110)
            item['staff_id'] = integer(pointer, True)
            item['club_pointer'] = integer(pointer+0x39)
            item['player_pointer'] = integer(pointer+0x61)
            if raw is None:
                flags.append('missing-staff')
            else:
                item['staff_sha256'] = hashlib.sha256(raw).hexdigest()
            if item['staff_id'] is not None and item['staff_id'] != index:
                flags.append('wrong-staff-id')
            if item['club_pointer'] is not None and item['club_pointer'] != club:
                flags.append('foreign-club')
            player = item['player_pointer']
            if player == 0:
                flags.append('null-player')
            elif player is not None:
                if not pb <= player < pb+np*70:
                    flags.append('outside-player')
                elif (player-pb) % 70:
                    flags.append('unaligned-player')
                else:
                    item['player_index'] = (player-pb)//70
                    item['player_id'] = integer(player, True)
                    raw = read(player, 70)
                    if raw is None:
                        flags.append('missing-player')
                    else:
                        item['player_sha256'] = hashlib.sha256(raw).hexdigest()
                    if item['player_id'] is not None and item['player_id'] != item['player_index']:
                        flags.append('wrong-player-id')
        item['flags'] = flags
        item['primary'] = flags[0] if flags else 'candidate'
        return item

    slots, seen_staff, seen_player = [], set(), set()
    for i in range(50):
        row = record(integer(club+0xd7+4*i))
        row['slot'] = i
        p, q = row['pointer'], row['player_pointer']
        row['duplicate_staff'] = p is not None and p in seen_staff
        row['duplicate_player'] = q not in (None, 0) and q in seen_player
        seen_staff.add(p)
        if q not in (None, 0):
            seen_player.add(q)
        slots.append(row)
    staff = []
    for i in range(ns):
        row = record(sb+i*110)
        row['associated'] = None if row['club_pointer'] is None else row['club_pointer'] == club
        staff.append(row)
    players = []
    for i in range(np):
        raw = read(pb+i*70, 70)
        rid = integer(pb+i*70, True)
        players.append(dict(index=i, id=rid, complete=raw is not None,
                            id_matches=None if rid is None else rid == i,
                            sha256=None if raw is None else hashlib.sha256(raw).hexdigest()))
    return dict(dimensions=dict(clubs=nc, nations=nn, staff=ns, players=np),
                binding=club, slots=slots, staff=staff, players=players)
