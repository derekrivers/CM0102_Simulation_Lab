#!/usr/bin/env python3
"""Pinned-PE structural inspection only; no emulator, game launch or admission.

Outputs normalized facts and hashes, never original bytes, names or runtime pointers.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import capstone

SPECIMEN = "0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86"
RANGES = {
    "mapping_resolver": (0x8968f0, 0x896a8e),
    "mapping_assignment": (0x896a90, 0x896c5d),
    "mapping_row_resolver": (0x8982b0, 0x8983ed),
    "ordinary_category": (0x53b900, 0x53b99f),
    "membership_assignment_caller_excerpt": (0x76263b, 0x76267d),
    "fifty_member_count_excerpt": (0x90d429, 0x90d45b),
    "player_table_loop_excerpt": (0x8b3cdc, 0x8b3d2e),
    "player_link_store_excerpt": (0x526535, 0x52654d),
}
# Frozen expected facts from manual pinned-instruction inspection. Excerpts are
# explicitly not function entries and cannot be invoked as qualified commands.
EXPECTED = {
    0x896939: ("mov", "cl, byte ptr [esp + 0x218]"),
    0x89694b: ("jg", "0x896a23"),
    0x89695c: ("call", "0x8982b0"),
    0x896985: ("mov", "eax, dword ptr [edx + edi + 2]"),
    0x8969a6: ("mov", "edx, dword ptr [eax + ebp + 0x61]"),
    0x8969b1: ("mov", "dword ptr [ecx], 0xffffffff"),
    0x8969cb: ("call", "0x53b900"),
    0x896a20: ("ret", "0xc"),
    0x896adb: ("mov", "bl, byte ptr [esp + 0x218]"),
    0x896ae4: ("jl", "0x896bf2"),
    0x896aea: ("cmp", "bl, 0x13"),
    0x896af3: ("mov", "edi, dword ptr [esp + 0x21c]"),
    0x896b74: ("call", "0x8982b0"),
    0x896b82: ("mov", "edx, dword ptr [esi + 0x601]"),
    0x896b96: ("mov", "eax, dword ptr [edi]"),
    0x896b98: ("mov", "dword ptr [ecx + edx + 2], eax"),
    0x896b9c: ("mov", "al, byte ptr [esi + 0x5f0]"),
    0x896ba6: ("lea", "eax, [esi + 0x38]"),
    0x896ba9: ("mov", "ecx, 0x10"),
    0x896bc6: ("mov", "dword ptr [eax], 0"),
    0x896bd4: ("mov", "byte ptr [esi + 0x5f0], dl"),
    0x896bda: ("add", "eax, 0x5c"),
    0x896be3: ("mov", "eax, 1"),
    0x896bef: ("ret", "0x10"),
    0x8982c8: ("call", "0x600a50"),
    0x8982e1: ("je", "0x8983e0"),
    0x8983e0: ("mov", "eax, dword ptr [esi]"),
    0x8983ea: ("ret", "8"),
    0x762656: ("cmp", "dword ptr [eax + 0x39], ecx"),
    0x76266a: ("call", "0x896a90"),
    0x90d42f: ("add", "ebp, 0xd7"),
    0x90d435: ("add", "eax, 0xd7"),
    0x90d43a: ("mov", "ecx, 0x32"),
    0x90d452: ("add", "eax, 4"),
    0x90d459: ("jne", "0x90d43f"),
    0x8b3cdc: ("mov", "ecx, dword ptr [0xae236c]"),
    0x8b3ce2: ("mov", "eax, dword ptr [0xae23c4]"),
    0x8b3cee: ("mov", "ecx, dword ptr [eax]"),
    0x8b3d26: ("add", "eax, 0x46"),
    0x52653f: ("mov", "eax, dword ptr [0xae23c4]"),
    0x52654a: ("mov", "dword ptr [esi + 0x61], ecx"),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(binary):
    raw = binary.read_bytes()
    require(len(raw) == 7192576 and digest(raw) == SPECIMEN, "wrong pinned specimen")
    require(capstone.__version__ == "5.0.7", "wrong decoder version")
    pe = struct.unpack_from("<I", raw, 60)[0]
    opt = pe + 24
    require(raw[:2] == b"MZ" and raw[pe:pe+4] == b"PE\0\0", "PE header")
    require(struct.unpack_from("<H", raw, opt)[0] == 0x10b, "PE32 required")
    require(struct.unpack_from("<I", raw, opt+28)[0] == 0x400000, "image base")
    count = struct.unpack_from("<H", raw, pe+6)[0]
    section = opt + struct.unpack_from("<H", raw, pe+20)[0]
    sections = [struct.unpack_from("<IIII", raw, section+40*i+8) for i in range(count)]

    def read(start, end):
        matches = [(size, offset, start-0x400000-rva)
                   for _, rva, size, offset in sections
                   if rva <= start-0x400000 and end-0x400000 <= rva+size]
        require(len(matches) == 1, "code range ambiguous/outside file extent")
        _, offset, delta = matches[0]
        result = raw[offset+delta:offset+delta+end-start]
        require(len(result) == end-start, "truncated code range")
        return result

    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    instructions, ranges = {}, {}
    for name, (start, end) in RANGES.items():
        code = read(start, end)
        decoded = list(decoder.disasm(code, start))
        require(decoded and decoded[-1].address+decoded[-1].size == end,
                "incomplete linear decode")
        for ins in decoded:
            instructions[ins.address] = (ins.mnemonic, ins.op_str)
        ranges[name] = {"start": f"{start:08x}", "end_exclusive": f"{end:08x}",
                        "sha256": digest(code), "decoded_instructions": len(decoded)}
    for address, expected in EXPECTED.items():
        require(instructions.get(address) == expected, f"static fact mismatch {address:08x}")
    return {
        "schema_version": 1, "method": "static-pinned-PE-inspection",
        "specimen_sha256": SPECIMEN, "specimen_bytes": len(raw),
        "decoder": "Capstone "+capstone.__version__,
        "inspector_sha256": digest(Path(__file__).read_bytes()),
        "decoder_module_sha256": digest(Path(capstone.__file__).read_bytes()),
        "ranges": ranges, "checked_instruction_facts": len(EXPECTED),
        "candidate": {"entry": "00896a90", "receiver": "captured tactical context",
            "arguments": ["club", "signed-low-byte index", "nonnull staff", "row mode"],
            "candidate_index_domain": [0, 19], "mapping_stride": 145,
            "mapping_slot_offset": 2, "mapping_slot_stride": 4,
            "success_eax": 1, "ret_bytes": 16,
            "cache_count_offset": 1520, "cache_first_active_offset": 56,
            "cache_record_stride": 92, "cache_record_count": 16},
        "readback": {"entry": "008968f0", "staff_player_link_offset": 97,
            "null_player_link_effect": "mapping DWORD becomes -1; returns zero",
            "staff_stride": 110, "ret_bytes": 12},
        "membership": {"club_list_offset": 215, "slots": 50,
            "stride": 4, "staff_reciprocal_club_offset": 57,
            "claim": "static structural corroboration only"},
        "original_calls_executed": 0, "production_admission": "none",
        "command_qualification": "pending-real-input-and-reviewed-execution",
        "limitations": ["No command or read-set lifetime is dynamically qualified",
            "Original assignment does not itself remove duplicate lineup entries",
            "Excerpts are not qualified entry-to-return paths",
            "No original Windows process, Bosman run or emulator invoked"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "output exists")
    result = inspect(args.binary)
    with args.output.open("x", encoding="utf8") as stream:
        stream.write(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"static_facts": result["checked_instruction_facts"],
                      "receipt_sha256": digest(args.output.read_bytes())}))
