#!/usr/bin/env python3
"""LAB-006: bounded read-only PE decoding; never executes original instructions."""
import argparse
import hashlib
import json
import os
import struct
from pathlib import Path

SPECIMEN_SHA256 = "0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86"
SPECIMEN_BYTES = 7192576
DECODER_VERSION = "5.0.7"
IMAGE_BASE = 0x400000
# Half-open boundaries and hashes retained from the independently reviewed R10
# static receipt. No runtime address, range or expected-fact override is accepted.
RANGES = (
    ("fifty_slots", 0x90D429, 0x90D45B,
     "63e2884d366467cf4a50a29a3d23fe93d44fe16336687219c69eab99e660a6ea", 15),
    ("association_caller", 0x76263B, 0x76267D,
     "655adb6b27dbaa74c797621725afdea729ff56a15df681964c730944c1327e2d", 23),
)
EXPECTED = {
    0x90D42F: ("add", "ebp, 0xd7"),
    0x90D435: ("add", "eax, 0xd7"),
    0x90D43A: ("mov", "ecx, 0x32"),
    0x90D452: ("add", "eax, 4"),
    0x90D459: ("jne", "0x90d43f"),
    0x762656: ("cmp", "dword ptr [eax + 0x39], ecx"),
    0x76266A: ("call", "0x896a90"),
}


class AdmissionError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise AdmissionError(reason)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def write_private(path, value):
    """Exclusive creation; no retry may replace prior attempt artifacts."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_specimen(raw):
    require(len(raw) == SPECIMEN_BYTES and digest(raw) == SPECIMEN_SHA256,
            "specimen_identity_rejected")


def pe_ranges(raw):
    """Extract only frozen file-backed executable ranges; PE bytes are not loaded."""
    require(len(raw) >= 64 and raw[:2] == b"MZ", "dos_header")
    pe = struct.unpack_from("<I", raw, 60)[0]
    require(pe + 24 <= len(raw) and raw[pe:pe + 4] == b"PE\0\0", "pe_header")
    machine, count = struct.unpack_from("<HH", raw, pe + 4)
    optional_size = struct.unpack_from("<H", raw, pe + 20)[0]
    optional = pe + 24
    section_table = optional + optional_size
    require(machine == 0x14C and 0 < count <= 96 and optional_size >= 32,
            "pe32_x86_required")
    require(section_table + count * 40 <= len(raw), "section_headers_missing")
    require(struct.unpack_from("<H", raw, optional)[0] == 0x10B and
            struct.unpack_from("<I", raw, optional + 28)[0] == IMAGE_BASE,
            "pe32_image_base")
    sections = []
    for index in range(count):
        header = section_table + index * 40
        _, rva, size, offset = struct.unpack_from("<IIII", raw, header + 8)
        flags = struct.unpack_from("<I", raw, header + 36)[0]
        require(offset + size <= len(raw), "section_file_extent")
        sections.append((rva, size, offset, flags))
    result = []
    for name, start, end, expected_hash, instruction_count in RANGES:
        matches = [(offset + start - IMAGE_BASE - rva, flags)
                   for rva, size, offset, flags in sections
                   if rva <= start - IMAGE_BASE and end - IMAGE_BASE <= rva + size]
        require(len(matches) == 1, "ambiguous_or_missing_range")
        offset, flags = matches[0]
        require(flags & 0x20000000, "range_not_executable_section")
        code = raw[offset:offset + end - start]
        require(len(code) == end - start and digest(code) == expected_hash,
                "frozen_range_identity")
        result.append((name, start, end, code, instruction_count))
    return result


def qualified_decoder():
    import capstone
    require(capstone.__version__ == DECODER_VERSION, "decoder_version_rejected")
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    decoder.detail = True
    decoder.skipdata = False
    return capstone, decoder


def signedness(mnemonic):
    if mnemonic in {"jl", "jle", "jg", "jge"}:
        return "signed-comparison"
    if mnemonic in {"ja", "jae", "jb", "jbe"}:
        return "unsigned-comparison"
    if mnemonic in {"je", "jne", "jz", "jnz"}:
        return "equality-bit-pattern"
    if mnemonic == "movsx":
        return "sign-extension"
    if mnemonic == "movzx":
        return "zero-extension"
    # CMP/SUB flag generation itself has no signed/unsigned interpretation;
    # the consuming branch decides. Ordinary MOV preserves a bit pattern.
    return "no-signed-interpretation-asserted"


def decode(code, start, end, capstone, decoder):
    require(len(code) == end - start, "decode_extent")
    rows, next_address = [], start
    for instruction in decoder.disasm(code, start):
        require(instruction.address == next_address and instruction.size > 0 and
                instruction.address + instruction.size <= end, "decode_gap_or_overrun")
        operands = []
        for operand in instruction.operands:
            item = {"width_bits": operand.size * 8,
                    "read": bool(operand.access & capstone.CS_AC_READ),
                    "write": bool(operand.access & capstone.CS_AC_WRITE)}
            if operand.type == capstone.x86.X86_OP_REG:
                item.update(kind="register", register=instruction.reg_name(operand.reg))
            elif operand.type == capstone.x86.X86_OP_IMM:
                item.update(kind="immediate", value=operand.imm)
            elif operand.type == capstone.x86.X86_OP_MEM:
                item.update(kind="memory", segment=instruction.reg_name(operand.mem.segment),
                            base=instruction.reg_name(operand.mem.base),
                            index=instruction.reg_name(operand.mem.index),
                            scale=operand.mem.scale, displacement=operand.mem.disp,
                            address_only=instruction.mnemonic == "lea")
                if instruction.mnemonic == "lea":
                    item.update(read=False, write=False)
            else:
                raise AdmissionError("unknown_operand_kind")
            operands.append(item)
        is_branch = instruction.group(capstone.CS_GRP_JUMP)
        is_call = instruction.group(capstone.CS_GRP_CALL)
        targets = [item["value"] for item in operands if item["kind"] == "immediate"]
        target = targets[0] if (is_branch or is_call) and targets else None
        read, written = instruction.regs_access()
        # Explicit memory operands above are static address expressions, never
        # fabricated dynamic addresses/values. Stack effects are implicit in x86.
        implicit_memory = []
        if instruction.mnemonic in {"call", "push"}:
            implicit_memory = [{"kind": "stack", "operation": "write", "width_bits": 32}]
        elif instruction.mnemonic in {"pop", "ret"}:
            implicit_memory = [{"kind": "stack", "operation": "read", "width_bits": 32}]
        rows.append({"address": instruction.address, "size": instruction.size,
                     "bytes_hex": instruction.bytes.hex(), "instruction_id": instruction.id,
                     "mnemonic": instruction.mnemonic, "operand_text": instruction.op_str,
                     "operands": operands, "signedness": signedness(instruction.mnemonic),
                     "registers_read": [instruction.reg_name(reg) for reg in read],
                     "registers_written": [instruction.reg_name(reg) for reg in written],
                     "eflags": instruction.eflags, "implicit_memory": implicit_memory,
                     "branch": is_branch, "call": is_call, "target": target,
                     "target_inside_excerpt": start <= target < end if target is not None else None,
                     "fallthrough": instruction.address + instruction.size,
                     "fallthrough_possible": instruction.mnemonic not in {"jmp", "ret"},
                     "group_ids": list(instruction.groups)})
        next_address += instruction.size
    require(rows and next_address == end, "incomplete_linear_decode")
    starts = {row["address"] for row in rows}
    for row in rows:
        require(not row["target_inside_excerpt"] or row["target"] in starts,
                "branch_into_instruction")
    return rows


def compare_facts(rows, expected):
    actual = {row["address"]: (row["mnemonic"], row["operand_text"]) for row in rows}
    return [{"address": address, "expected": list(fact),
             "actual": list(actual[address]) if address in actual else None,
             "equal": actual.get(address) == fact}
            for address, fact in sorted(expected.items())]


def controls(capstone, decoder):
    """Independent, invented instruction fixture; no original bytes or state."""
    # cmp DWORD [eax+39h],ecx; jne +0; movsx ecx,BYTE [eax];
    # movzx ecx,BYTE [eax]; jl +0; call 0x1012; nop.
    code = bytes.fromhex("39483975000fbe080fb6087c00e80000000090")
    rows = decode(code, 0x1000, 0x1000 + len(code), capstone, decoder)
    expected = {0x1000: ("cmp", "dword ptr [eax + 0x39], ecx"),
                0x1003: ("jne", "0x1005"), 0x1005: ("movsx", "ecx, byte ptr [eax]"),
                0x1008: ("movzx", "ecx, byte ptr [eax]"),
                0x100B: ("jl", "0x100d"), 0x100D: ("call", "0x1012")}
    positive = all(item["equal"] for item in compare_facts(rows, expected))
    positive = positive and rows[0]["operands"][0]["width_bits"] == 32
    positive = positive and rows[0]["operands"][0]["read"] and not rows[0]["operands"][0]["write"]
    positive = positive and rows[2]["signedness"] == "sign-extension"
    positive = positive and rows[3]["signedness"] == "zero-extension"
    positive = positive and rows[4]["signedness"] == "signed-comparison"
    positive = positive and rows[5]["call"] and rows[5]["target"] == 0x1012
    result = {"known_synthetic_fixture": positive}
    defects = {"read_width": (0, 0x38), "club_displacement": (2, 0x38),
               "branch_predicate": (3, 0x74), "branch_target": (4, 3),
               "extension_signedness": (6, 0xB6),
               "comparison_signedness": (11, 0x72), "call_target": (14, 1)}
    for name, (offset, byte) in defects.items():
        changed = bytearray(code)
        changed[offset] = byte
        defective_rows = decode(bytes(changed), 0x1000, 0x1000 + len(code), capstone, decoder)
        result[name] = not all(item["equal"] for item in compare_facts(defective_rows, expected))
    result["omitted_instruction"] = not all(item["equal"] for item in compare_facts(rows[1:], expected))
    try:
        decode(b"\xe8\x00", 0x1000, 0x1002, capstone, decoder)
        result["incomplete_boundary"] = False
    except AdmissionError:
        result["incomplete_boundary"] = True
    try:
        validate_specimen(bytes(SPECIMEN_BYTES))
        result["wrong_specimen"] = False
    except AdmissionError:
        result["wrong_specimen"] = True
    require(all(result.values()), "instruction_controls_failed")
    return result


def run(executable_path, attempt_path):
    """Fixed adapter endpoint; caller owns immutable attempt and manifest pins.

    Requires the qualified oracle interpreter. Returns sanitized outcome only.
    Raw facts stay in lab006-private.json under the private lab attempt directory.
    """
    attempt = Path(attempt_path)
    require(not attempt.is_symlink() and attempt.is_dir(), "regular_attempt_directory_required")
    raw_path, public_path = attempt / "lab006-private.json", attempt / "lab006-result.json"
    require(not raw_path.exists() and not public_path.exists(), "artifact_exists")
    outcome = {"execution_status": "failed", "comparison_verdict": "not-run",
               "details": {"hypothesis_conclusion": "unresolved", "original_instructions_executed": 0,
                           "planned_case_count": 2, "completed_case_count": 0,
                           "unstarted_case_count": 2, "failed_case_count": 0,
                           "production_admission": "none"}}
    private = {"schema_version": 1, "campaign": "LAB-006-v1", "ranges": [],
               "specimen_sha256": SPECIMEN_SHA256, "original_instructions_executed": 0,
               "cases": [{"name": name, "start": start, "end_exclusive": end,
                          "disposition": "unstarted"} for name, start, end, _, _ in RANGES]}
    try:
        capstone, decoder = qualified_decoder()
        private["controls"] = controls(capstone, decoder)
        source = Path(executable_path)
        require(not source.is_symlink() and source.is_file() and source.stat().st_size == SPECIMEN_BYTES,
                "specimen_identity_rejected")
        with source.open("rb") as stream:
            raw = stream.read(SPECIMEN_BYTES + 1)
        validate_specimen(raw)
        private["decoder"] = {"version": capstone.__version__,
                              "module_sha256": digest(Path(capstone.__file__).read_bytes())}
        private["source_sha256"] = digest(Path(__file__).read_bytes())
        all_rows = []
        for index, (name, start, end, code, expected_count) in enumerate(pe_ranges(raw)):
            private["cases"][index]["disposition"] = "failed"
            rows = decode(code, start, end, capstone, decoder)
            require(len(rows) == expected_count, "instruction_count_mismatch")
            private["ranges"].append({"name": name, "start": start, "end_exclusive": end,
                                      "sha256": digest(code), "instructions": rows})
            all_rows.extend(rows)
            private["cases"][index]["disposition"] = "completed"
        private["fact_comparison"] = compare_facts(all_rows, EXPECTED)
        equal = all(item["equal"] for item in private["fact_comparison"])
        private["follow_up_dependencies"] = [
            {"address": row["address"], "kind": "call" if row["call"] else "branch",
             "target": row["target"]}
            for row in all_rows if (row["call"] or row["branch"]) and not row["target_inside_excerpt"]]
        private["scope"] = "static predicates only; dynamic reads, entry conditions and callee behavior unavailable"
        outcome.update(execution_status="succeeded", comparison_verdict="equal" if equal else "different")
        outcome["details"].update(
            hypothesis_conclusion="supported" if equal else "contradicted",
            hypothesis_reason="frozen_predicates_reproduced" if equal else "frozen_predicates_contradicted",
            range_count=len(private["ranges"]), instruction_count=len(all_rows),
            checked_fact_count=len(EXPECTED), matched_fact_count=sum(item["equal"] for item in private["fact_comparison"]),
            explicit_memory_read_count=sum(operand["kind"] == "memory" and operand["read"]
                                           for row in all_rows for operand in row["operands"]),
            branch_count=sum(row["branch"] for row in all_rows),
            call_count=sum(row["call"] for row in all_rows),
            external_dependency_count=len(private["follow_up_dependencies"]),
            control_count=len(private["controls"]), control_pass_count=sum(private["controls"].values()),
            instruction_facts_sha256=digest(canonical(all_rows)))
    except AdmissionError as error:
        private["failure"] = str(error)
        outcome["execution_status"] = "rejected" if str(error) in {
            "specimen_identity_rejected", "decoder_version_rejected"} else "failed"
        outcome["details"]["failure_code"] = str(error)
    except Exception as error:
        # Full exception messages can contain private paths; keep public type only.
        private["failure_type"] = type(error).__name__
        outcome["details"]["failure_code"] = "inspection_exception"
    for disposition in ("completed", "unstarted", "failed"):
        outcome["details"][disposition + "_case_count"] = sum(
            case["disposition"] == disposition for case in private["cases"])
    write_private(raw_path, private)
    outcome["details"]["private_receipt_sha256"] = digest(raw_path.read_bytes())
    write_private(public_path, outcome)
    return outcome


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("attempt", type=Path)
    args = parser.parse_args()
    result = run(args.executable, args.attempt)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["execution_status"] == "succeeded" else 1)
