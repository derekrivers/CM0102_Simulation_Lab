"""LAB-005 decoder B: unpacked record slices, independent predicates/precedence."""
import hashlib
import struct


class DecodeBoundary(ValueError):
    def __init__(self, reason, dimensions=None):
        super().__init__(reason)
        self.dimensions = dimensions


def decode(regions):
    spans = sorted(((start, start+len(data), memoryview(data)) for start, data in regions),
                   key=lambda span: span[0])
    end = 0
    for low, high, _ in spans:
        if low < end or low < 0 or high <= low or high > 0x100000000:
            raise DecodeBoundary('invalid-or-overlapping-regions')
        end = high

    def block(start, length):
        matches = [data[start-low:start-low+length] for low, high, data in spans
                   if low <= start and start+length <= high]
        return matches[0] if len(matches) == 1 else None

    def word(at, signed=False):
        data = block(at, 4)
        return None if data is None else struct.unpack('<i' if signed else '<I', data)[0]

    layout = {key: word(address) for key, address in (
        ('clubs', 0xae235c), ('nations', 0xae2350), ('staff', 0xae2364),
        ('players', 0xae236c), ('cb', 0xae23b4), ('sb', 0xae23bc), ('pb', 0xae23c4))}
    if any(x is None for x in layout.values()):
        raise DecodeBoundary('missing-globals')
    if (layout['nations'] <= 0 or layout['nations']*2 >= layout['clubs'] or
            layout['clubs'] > 10000 or not 16 < layout['staff'] <= 100000 or
            not 0 < layout['players'] <= 100000):
        raise DecodeBoundary('dimensions')
    bases = [layout['cb']+581*i for i in range(layout['clubs']-2*layout['nations'])]
    human = []
    for ordinal, address in enumerate(bases):
        m = word(address+207)
        if m is None:
            raise DecodeBoundary('incomplete-binding-search',
                                 {k: layout[k] for k in ('clubs', 'nations', 'staff', 'players')})
        delta = m-layout['sb']
        quotient, remainder = divmod(delta, 110)
        if remainder == 0 and layout['staff']-16 <= quotient < layout['staff']:
            identity, club_id, backpointer = word(m, True), word(address, True), word(m+57)
            if identity is None or club_id is None or backpointer is None:
                raise DecodeBoundary('incomplete-binding-search',
                                     {k: layout[k] for k in ('clubs', 'nations', 'staff', 'players')})
            if identity == quotient and club_id == ordinal and backpointer == address:
                human.append(address)
    if len(human) != 1:
        raise DecodeBoundary('unique-binding-unavailable',
                             {k: layout[k] for k in ('clubs', 'nations', 'staff', 'players')})
    owner = human[0]

    def parse(address):
        output = {'pointer': address, 'staff_index': None, 'staff_id': None,
                  'club_pointer': None, 'player_pointer': None, 'player_index': None,
                  'player_id': None, 'staff_sha256': None, 'player_sha256': None}
        problems = {}
        problems['missing-slot'] = address is None
        inside = address is not None and 0 <= address-layout['sb'] < 110*layout['staff']
        problems['outside-staff'] = address is not None and not inside
        aligned = inside and (address-layout['sb']) % 110 == 0
        problems['unaligned-staff'] = inside and not aligned
        if aligned:
            output.update(staff_index=(address-layout['sb'])//110,
                          staff_id=word(address, True), club_pointer=word(address+57),
                          player_pointer=word(address+97))
            data = block(address, 110)
            problems['missing-staff'] = data is None
            if data is not None:
                output['staff_sha256'] = hashlib.sha256(data).hexdigest()
            problems['wrong-staff-id'] = output['staff_id'] is not None and output['staff_id'] != output['staff_index']
            problems['foreign-club'] = output['club_pointer'] is not None and output['club_pointer'] != owner
            link = output['player_pointer']
            problems['null-player'] = link == 0
            if link not in (None, 0):
                offset = link-layout['pb']
                within = 0 <= offset < 70*layout['players']
                problems['outside-player'] = not within
                problems['unaligned-player'] = within and offset % 70 != 0
                if within and offset % 70 == 0:
                    output['player_index'] = offset//70
                    output['player_id'] = word(link, True)
                    content = block(link, 70)
                    problems['missing-player'] = content is None
                    if content is not None:
                        output['player_sha256'] = hashlib.sha256(content).hexdigest()
                    problems['wrong-player-id'] = output['player_id'] is not None and output['player_id'] != offset//70
        precedence = ('missing-slot', 'outside-staff', 'unaligned-staff', 'missing-staff',
                      'wrong-staff-id', 'foreign-club', 'null-player', 'outside-player',
                      'unaligned-player', 'missing-player', 'wrong-player-id')
        output['flags'] = [name for name in precedence if problems.get(name, False)]
        output['primary'] = next(iter(output['flags']), 'candidate')
        return output

    entries = [parse(word(owner+215+4*n)) for n in range(50)]
    for n, entry in enumerate(entries):
        entry['slot'] = n
        entry['duplicate_staff'] = entry['pointer'] is not None and any(
            prior['pointer'] == entry['pointer'] for prior in entries[:n])
        entry['duplicate_player'] = entry['player_pointer'] not in (None, 0) and any(
            prior['player_pointer'] == entry['player_pointer'] for prior in entries[:n])
    inventory = [parse(layout['sb']+110*n) for n in range(layout['staff'])]
    for entry in inventory:
        value = entry['club_pointer']
        entry['associated'] = value == owner if value is not None else None
    player_inventory = []
    for n in range(layout['players']):
        address = layout['pb']+70*n
        content = block(address, 70)
        value = word(address, True)
        player_inventory.append({'index': n, 'id': value, 'complete': content is not None,
                                 'id_matches': None if value is None else value == n,
                                 'sha256': hashlib.sha256(content).hexdigest() if content is not None else None})
    return {'dimensions': {k: layout[k] for k in ('clubs', 'nations', 'staff', 'players')},
            'binding': owner, 'slots': entries, 'staff': inventory, 'players': player_inventory}
