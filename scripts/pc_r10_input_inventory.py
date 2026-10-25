#!/usr/bin/env python3
"""Read-only pinned real-input inventory; no execution, mutation or admission.

No project parser imports. Output contains structural counts/hashes only.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

IMAGE = "ae11ce3ef6267ad55be6aa6387f676704b1bb8a6310507db6c5ccfe494d45c3a"
HEAP = "30ee2baefad8f57f8760f30abc076586f2d13339bb1629f75346a5dcbc1357a0"
SPARSE = "014808018f7b20f60abaac5c71a0c509747259e309563650afe0d0cc79da6f40"
GLOBALS = [0xae235c, 0xae2350, 0xae2364, 0xae23b4, 0xae23bc,
           0xde1d08, 0xb63c98, 0xae2c90]


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(path, identity, limit):
    require(path.is_file() and not path.is_symlink(), "unsupported input object")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit and sha(data) == identity, "input identity mismatch")
    return data


class State:
    def __init__(self, path, kind):
        if kind == "retained":
            self.regions = [(0x400000, pinned(path / "image.bin", IMAGE, 12000000)),
                            (0x70000000, pinned(path / "heap.bin", HEAP, 120000000))]
            self.identities = [IMAGE, HEAP]
        else:
            raw = pinned(path, SPARSE, 16778000)
            require(raw[:8] == b"PCR5SP01" and raw[-8:] == b"PCR5DONE", "missing footer")
            self.regions = []
            pos = 8
            while pos < len(raw) - 8:
                require(pos + 8 <= len(raw) - 8, "truncated header")
                address, size = struct.unpack_from("<II", raw, pos)
                pos += 8
                require(0 < size <= 8388608 and address + size <= 2**32 and
                        pos + size <= len(raw) - 8, "invalid extent")
                require(not any(address < a + len(b) and a < address + size
                                for a, b in self.regions), "overlapping extents")
                self.regions.append((address, raw[pos:pos + size]))
                pos += size
            require(pos == len(raw) - 8 and len(self.regions) == 16, "invalid region count")
            require([(a, len(b)) for a, b in self.regions[:8]] ==
                    [(a, 4) for a in GLOBALS], "invalid global inventory")
            self.identities = [SPARSE]

    def read(self, address, size):
        require(size >= 0 and 0 <= address <= address + size <= 2**32, "invalid read")
        for base, data in self.regions:
            if base <= address and address + size <= base + len(data):
                return data[address - base:address - base + size]
        raise ValueError("required extent unavailable")

    def integer(self, address, width=4, signed=False):
        return int.from_bytes(self.read(address, width), "little", signed=signed)


def inventory(state):
    u = state.integer
    clubs, nations, staff, cb, sb, ctx, reg, _ = [u(a) for a in GLOBALS]
    require(0 < 2 * nations < clubs <= 10000 and 16 < staff <= 100000, "invalid counts")
    state.read(cb, clubs * 581)
    state.read(sb, staff * 110)
    state.read(ctx, 0x605)
    mapping = u(ctx + 0x601)
    state.read(mapping, (clubs + 32) * 145)
    rows, nr = u(reg), u(reg + 4)
    require(nr == 16, "unsupported registry count")
    state.read(rows, nr * 0xa6ef)
    counts = [u(ctx + offset, signed=True) for offset in (0x5fd, 0x5f5)]
    require(all(0 < n <= 256 for n in counts), "unsupported banks")
    for offset, count in zip((0x5f9, 0x5f1), counts):
        state.read(u(ctx + offset), count * 6371)
    bindings = []
    for index in range(clubs - 2 * nations):
        club = cb + index * 581
        manager = u(club + 0xcf)
        if not (sb <= manager < sb + staff * 110 and (manager - sb) % 110 == 0):
            continue
        mid = u(manager, signed=True)
        if not staff - 16 <= mid < staff:
            continue
        require(mid == (manager - sb) // 110 and u(club, signed=True) == index and
                u(manager + 0x39) == club, "invalid reciprocal human binding")
        ri = mid - staff + 16
        row = rows + ri * 0xa6ef
        slots = [u(mapping + index * 145 + 2 + i * 4, signed=True) for i in range(20)]
        require(all(x == -1 or 0 <= x < staff for x in slots), "mapping ID outside staff")
        linked = sum(x >= 0 and u(sb + x * 110 + 0x61) != 0 for x in slots)
        associated = []
        for sid in range(staff):
            address = sb + sid * 110
            if u(address + 0x39) == club and u(address + 0x61) != 0:
                require(u(address, signed=True) == sid, "associated staff ID mismatch")
                associated.append(sid)
        member_ids = []
        nulls = 0
        player_links = 0
        id_mismatch = 0
        club_mismatch = 0
        invalid_pointer = 0
        minus_one = 0
        for offset in range(50):
            pointer = u(club + 0xd7 + offset * 4)
            if pointer == 0:
                nulls += 1
                continue
            if pointer == 0xffffffff:
                minus_one += 1
                continue
            if not (sb <= pointer < sb + staff * 110 and (pointer - sb) % 110 == 0):
                invalid_pointer += 1
                continue
            sid = (pointer - sb) // 110
            id_mismatch += u(pointer, signed=True) != sid
            club_mismatch += u(pointer + 0x39) != club
            member_ids.append(sid)
            player_links += u(pointer + 0x61) != 0
        duplicates = len(member_ids) - len(set(member_ids))
        bindings.append({"candidate_club_membership_slots": 50,
                         "candidate_club_membership_null": nulls,
                         "candidate_club_membership_minus_one": minus_one,
                         "candidate_club_membership_valid_staff_pointers": len(member_ids),
                         "candidate_club_membership_invalid_pointers": invalid_pointer,
                         "candidate_club_membership_duplicate_ids": duplicates,
                         "candidate_member_nonnull_player_links": player_links,
                         "candidate_member_id_mismatches": id_mismatch,
                         "candidate_member_club_mismatches": club_mismatch,
                         "candidate_member_ids_sha256": sha(b"".join(
                             struct.pack("<i", x) for x in member_ids)),
                         "standard_mapping_entries": 20,
                         "standard_mapping_empty": slots.count(-1),
                         "standard_mapping_nonempty": sum(x >= 0 for x in slots),
                         "nonnull_link_for_mapped_staff": linked,
                         "staff_same_club_pointer_and_nonnull_61": len(associated),
                         "associated_staff_id_sequence_sha256": sha(b"".join(
                             struct.pack("<i", x) for x in associated)),
                         "mapping_row_sha256": sha(state.read(mapping + index * 145, 145)),
                         "registry_row_sha256": sha(state.read(row, 0xa6ef)),
                         "context_cache_count": u(ctx + 0x5f0, 1),
                         "guard": u(row + 0x9a01),
                         "option_two": u(row + 0x9b25, 1),
                         "selected_slot": u(row + 0x9a69, 1)})
    require(len(bindings) == 1, "requires exactly one real reciprocal human binding")
    return {"schema_version": 1, "input_sha256": state.identities,
            "reciprocal_human_binding_count": len(bindings), "bindings": bindings,
            "ordinary_bank_counts": counts,
            "nonempty_input_qualified": False, "production_admission": "none",
            "scope": "structural inventory only; +0x39/+0x61 association is not squad semantics or lifetime qualification",
            "original_windows_process_launched": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("retained", "sparse"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "output already exists")
    with args.output.open("x", encoding="utf8") as stream:
        try:
            result = inventory(State(args.input, args.kind))
        except (ValueError, OSError, struct.error) as error:
            result = {"execution_status": "failed", "reason": str(error),
                      "production_admission": "none"}
            # OSError messages can contain private paths; retain only the type.
            if isinstance(error, OSError):
                result["reason"] = type(error).__name__
            failed = True
        else:
            result["execution_status"] = "completed-structural-inventory"
            failed = False
        result["source_sha256"] = sha(Path(__file__).read_bytes())
        result["input_kind"] = args.kind
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"receipt_sha256": sha(args.output.read_bytes()),
                      "execution_status": result["execution_status"]}))
    if failed:
        raise SystemExit(1)



if __name__ == "__main__":
    main()
