#!/usr/bin/env python3
"""Frozen retained-only original slot-zero assignment qualification.

Research only. No original process, code patch, synthetic input or admission.
"""
import argparse
import copy
import hashlib
import json
import struct
import sys
import time
from pathlib import Path
import capstone
import unicorn
from qualify_human_registry import (Oracle, Snapshot, locate, checked, require,
    digest, canonical, SPECIMEN, SOURCE_CAPTURE, IMAGE_HASH, HEAP_HASH, STACK)

# Complete original routines. CALL targets are separately restricted, so diagnostic
# code may be inspected up to its first unavailable call but never executed past it.
RANGES = [(0x896a90, 0x896c5d), (0x8968f0, 0x896a8e),
          (0x8982b0, 0x8983ed), (0x600a50, 0x600c88), (0x53b900, 0x53b99f)]
CALLS = {0x896b74: 0x8982b0, 0x89695c: 0x8982b0,
         0x8982c8: 0x600a50, 0x600b84: 0x53b900, 0x8969cb: 0x53b900}


def candidates(snapshot, state):
    sb, pb, pc = (snapshot.u32(a) for a in (0xae23bc, 0xae23c4, 0xae236c))
    require(0 < pc <= 100000, "player count")
    table = snapshot.read(pb, pc*70)
    require(all(struct.unpack_from("<i", table, i*70)[0] == i for i in range(pc)),
            "player table IDs")
    require(snapshot.read(state["context"]+0x5f0, 1) == b"\0", "requires zero cache")
    require(all(snapshot.s32(state["mapping"]+state["club_id"]*145+2+4*i) == -1
                for i in range(20)), "requires actual initially empty mapping")
    found, invalid, mismatched = [], 0, 0
    for index in range(50):
        ptr = snapshot.u32(state["club"]+0xd7+4*index)
        if not(sb <= ptr < sb+state["staff"]*110 and (ptr-sb)%110 == 0):
            invalid += 1
            continue
        sid = (ptr-sb)//110
        require(snapshot.s32(ptr) == sid, "member ID mismatch")
        link = snapshot.u32(ptr+0x61)
        require(pb <= link < pb+pc*70 and (link-pb)%70 == 0, "member player extent")
        player_id = (link-pb)//70
        require(snapshot.s32(link) == player_id, "member player ID mismatch")
        if snapshot.u32(ptr+0x39) != state["club"]:
            mismatched += 1
            continue
        found.append((sid, ptr, player_id, link))
    require(len(found) == 43 and len(set(x[0] for x in found)) == 43 and
            invalid == 2 and mismatched == 5, "pinned membership structure")
    found.sort()
    chosen = found[:2]
    identity = {"player_table_sha256": digest(table), "player_count": pc,
        "structural_candidates": 43, "unqualified_list_entries": 7,
        "selected_records": [{"staff_sha256": digest(snapshot.read(p, 110)),
            "player_sha256": digest(snapshot.read(q, 70))} for _, p, _, q in chosen]}
    return chosen, identity


class Boundary(ValueError):
    pass


class AssignmentOracle(Oracle):
    def __init__(self, raw, snapshot, state, chosen):
        super().__init__(raw, snapshot, state)
        require(capstone.__version__ == "5.0.7", "decoder version")
        self.decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.instruction_sizes = {}
        for start, end in RANGES:
            decoded = list(self.decoder.disasm(bytes(self.uc.mem_read(start, end-start)), start))
            require(decoded and decoded[-1].address+decoded[-1].size == end,
                    "incomplete frozen instruction decode")
            for ins in decoded:
                self.instruction_sizes[ins.address] = ins.size
        self.target = state["mapping"]+state["club_id"]*145+2
        self.fields = {"club_id": (state["club"], 4),
            "club_manager": (state["club"]+0xcf, 4),
            "manager_id": (state["manager"], 4),
            "staff_count": (0xae2364, 4), "club_count": (0xae235c, 4),
            "nation_count": (0xae2350, 4), "staff_table": (0xae23bc, 4),
            "mapping_table": (state["context"]+0x601, 4),
            "cache_count": (state["context"]+0x5f0, 1),
            "slot_zero": (self.target, 4)}
        for i, (_, ptr, _, _) in enumerate(chosen):
            self.fields[f"candidate_{i}_id"] = (ptr, 4)
            self.fields[f"candidate_{i}_player_link"] = (ptr+0x61, 4)
        self.ids = [x[0] for x in chosen]
        self.pc, self.decoded, self.boundary = None, None, None
        self.ordered_reads, self.current_starts = [], []
        self.write_pcs = []

    def censor(self, kind, field, width=None):
        self.boundary = {"pc": f"{self.pc:08x}", "instruction": self.decoded,
                         "kind": kind, "field": field, "width": width}
        raise Boundary("frozen boundary")

    def instruction(self, uc, address, size, unused):
        self.pc = address
        ins = list(self.decoder.disasm(bytes(uc.mem_read(address, size)), address))
        require(len(ins) == 1 and ins[0].size == size, "instruction decode")
        self.decoded = ins[0].mnemonic+(" "+ins[0].op_str if ins[0].op_str else "")
        if self.instruction_sizes.get(address) != size:
            self.censor("instruction", "outside-frozen-instruction-starts")
        if ins[0].mnemonic == "call" and (address not in CALLS or
                ins[0].op_str != hex(CALLS[address])):
            self.censor("call", "unqualified-original-call")
        if ins[0].mnemonic in ("int", "syscall", "sysenter"):
            self.censor("instruction", "system-boundary")
        self.starts.add(address)
        self.current_starts.append(f"{address:08x}")

    def read(self, uc, access, address, size, value, unused):
        if STACK <= address and address+size <= STACK+0x10000:
            return
        field = next((k for k, v in self.fields.items() if v == (address, size)), None)
        if field is None:
            self.censor("read", "outside-frozen-fields", size)
        self.reads.add((address, size))
        self.ordered_reads.append({"pc": f"{self.pc:08x}", "field": field, "width": size})

    def write(self, uc, access, address, size, value, unused):
        if STACK <= address and address+size <= STACK+0x10000:
            return
        if (address, size) not in self.allowed_writes or address != self.target:
            self.censor("write", "outside-slot-zero", size)
        require(value in self.ids, "unadmitted staff ID write")
        self.writes.append({"field": "slot_zero", "width": size,
                            "candidate": self.ids.index(value)})
        self.write_pcs.append(f"{self.pc:08x}")

    def check_complete(self, candidate):
        changes = {} if candidate is None else {
            self.target-self.state["row"]+i: b
            for i, b in enumerate(self.ids[candidate].to_bytes(4, "little"))}
        self.full_state(changes)


def expected_writes(kind, candidate):
    return [] if kind == "read" else [{"field": "slot_zero", "width": 4,
                                       "candidate": candidate}]


def verify(observed, kind, candidate, state_sha256):
    require(observed["ordered_writes"] == expected_writes(kind, candidate), "ordered effects")
    require(observed["ordered_write_pcs"] == ([] if kind == "read" else ["00896b98"]),
            "write PCs")
    require(observed["returned"] == (candidate if kind == "read" else "success-one"), "return")
    require(observed["rng_draws"] == 0 and observed["abi_checked"] is True, "RNG/ABI")
    require(observed["heap_sha256"] == state_sha256, "complete state digest")


def state_hash(oracle):
    h = hashlib.sha256()
    for address, data in oracle.capture_state():
        h.update(struct.pack("<II", address, len(data))); h.update(data)
    return h.hexdigest()


def generate(binary, capture, attempts):
    raw = checked(binary, SPECIMEN)
    snapshot = Snapshot(capture)
    state = locate(snapshot)
    chosen, identity = candidates(snapshot, state)
    oracle = AssignmentOracle(raw, snapshot, state, chosen)
    cases = []
    current = None

    def run(kind, candidate):
        nonlocal current
        oracle.current_starts, oracle.ordered_reads, oracle.write_pcs = [], [], []
        oracle.boundary = None
        attempt = {"kind": kind, "candidate": candidate, "status": "started"}
        attempts.append(attempt)
        args = [state["club"], 0, 0] if kind == "read" else [state["club"], 0, chosen[candidate][1], 0]
        entry = 0x8968f0 if kind == "read" else 0x896a90
        returned = (0 if candidate is None else chosen[candidate][1]) if kind == "read" else 1
        started = time.monotonic()
        try:
            oracle.call(entry, args, state["context"],
                        [] if kind == "read" else [(oracle.target, 4)], returned)
        finally:
            attempt.update(elapsed_seconds=time.monotonic()-started,
                boundary=copy.deepcopy(oracle.boundary), pc=f"{oracle.pc:08x}",
                instruction=oracle.decoded, partial_writes=copy.deepcopy(oracle.writes),
                ordered_reads=copy.deepcopy(oracle.ordered_reads))
        if kind != "read":
            current = candidate
        oracle.check_complete(current)
        case = {"kind": kind, "candidate": candidate,
            "ordered_writes": copy.deepcopy(oracle.writes),
            "ordered_write_pcs": oracle.write_pcs.copy(),
            "ordered_reads": copy.deepcopy(oracle.ordered_reads),
            "instruction_starts": oracle.current_starts.copy(),
            "returned": candidate if kind == "read" else "success-one",
            "rng_draws": 0, "abi_checked": True, "heap_sha256": state_hash(oracle)}
        verify(case, kind, candidate, case["heap_sha256"])
        attempt["status"] = "succeeded"
        cases.append(case)
        return case

    run("read", None)
    for candidate in (0, 0, 1):
        run("assign", candidate); run("read", candidate)
    checkpoint = oracle.capture_state()
    first = [run("assign", 0), run("read", 0)]
    final = oracle.capture_state()
    oracle.restore_state(checkpoint)
    current = 1
    second = [run("assign", 0), run("read", 0)]
    require(first == second and oracle.capture_state() == final, "checkpoint continuation")
    controls = {}
    for name, mutate in [
        ("wrong-player", lambda c: c["ordered_writes"][0].update(candidate=1)),
        ("wrong-slot", lambda c: c["ordered_writes"][0].update(field="slot_one")),
        ("wrong-width", lambda c: c["ordered_writes"][0].update(width=2)),
        ("omitted-repeat", lambda c: c.update(ordered_writes=[])),
        ("extra-cache-write", lambda c: c["ordered_writes"].append({"field": "cache_count", "width": 1, "candidate": 0})),
        ("wrong-original-PC", lambda c: c.update(ordered_write_pcs=["008969b1"])),
        ("extra-RNG", lambda c: c.update(rng_draws=1)),
        ("wrong-return", lambda c: c.update(returned=0)),
        ("unchecked-ABI", lambda c: c.update(abi_checked=False)),
        ("immutable-state-corruption", lambda c: c.update(heap_sha256="0"*64))]:
        candidate_case = copy.deepcopy(cases[3])  # actual repeated assignment to candidate zero
        mutate(candidate_case)
        try:
            verify(candidate_case, "assign", 0, cases[3]["heap_sha256"])
        except ValueError:
            controls[name] = True
        else:
            raise ValueError("nondiscriminating control")
    for name, mutate in [
        ("readback-cleanup", lambda c: c.update(ordered_writes=[{"field": "slot_zero", "width": 4, "candidate": None}])),
        ("wrong-readback-result", lambda c: c.update(returned=1))]:
        read_case = copy.deepcopy(cases[2])
        mutate(read_case)
        try:
            verify(read_case, "read", 0, cases[2]["heap_sha256"])
        except ValueError:
            controls[name] = True
        else:
            raise ValueError("nondiscriminating readback control")
    probe_checkpoint = oracle.capture_state()
    probes = []
    for label, args, boundary_pc in [
        ("null-club", [0, 0, chosen[0][1], 0], "00896abd"),
        ("negative-index", [state["club"], 0xffffffff, chosen[0][1], 0], "00896c06"),
        ("index-twenty", [state["club"], 20, chosen[0][1], 0], "00896c06"),
        ("null-staff", [state["club"], 0, 0, 0], "00896b12")]:
        oracle.restore_state(probe_checkpoint)
        oracle.boundary = None; oracle.ordered_reads = []; oracle.current_starts = []; oracle.write_pcs = []
        attempt = {"kind": label, "status": "started"}; attempts.append(attempt)
        try:
            oracle.call(0x896a90, args, state["context"], [(oracle.target, 4)])
        except Boundary:
            require(oracle.boundary["pc"] == boundary_pc and not oracle.writes,
                    "unexpected unsupported boundary/effects")
        else:
            raise ValueError("unsupported probe returned")
        finally:
            attempt.update(boundary=copy.deepcopy(oracle.boundary),
                partial_writes=copy.deepcopy(oracle.writes),
                ordered_reads=copy.deepcopy(oracle.ordered_reads))
        oracle.check_complete(0)
        attempt["status"] = "censored"
        probes.append(copy.deepcopy(attempt))
    oracle.restore_state(probe_checkpoint)
    oracle.check_complete(0)
    dependencies = [Path(__file__).name, "qualify_human_registry.py", "qualify_manager_bound_plan.py"]
    return {"schema_version": 1, "specimen_sha256": SPECIMEN,
        "capture": {"source_capture_sha256": SOURCE_CAPTURE, "image_sha256": IMAGE_HASH,
                    "heap_sha256": HEAP_HASH}, "initialized_lifetime": identity,
        "source_dependencies": {n: digest((Path(__file__).parent/n).read_bytes()) for n in dependencies},
        "upstream_lock_sha256": digest((Path(__file__).parent.parent/"config/upstream-lock.json").read_bytes()),
        "tool_versions": {"python": sys.version.split()[0], "unicorn": unicorn.__version__, "capstone": capstone.__version__},
        "tool_sha256": {"python": digest(Path(sys.executable).read_bytes()),
                        "unicorn_module": digest(Path(unicorn.__file__).read_bytes()),
                        "capstone_module": digest(Path(capstone.__file__).read_bytes())},
        "instruction_ranges": [{"start": f"{a:08x}", "end_exclusive": f"{b:08x}",
            "sha256": digest(bytes(oracle.uc.mem_read(a, b-a)))} for a, b in RANGES],
        "cases": cases, "successful_calls": len(cases), "censored_calls": len(probes),
        "probes": probes, "defect_controls": controls, "checkpoint_continuation": "exact",
        "complete_heap_and_loaded_official_image_checked_after_every_call": True,
        "host_domain_rejection": "not-tested-no-production-validator",
        "limits": {"maximum_calls": 15, "instructions_per_call": 3000, "emulator_microseconds": 100000},
        "production_admission": "none", "original_windows_process_launched": False,
        "limitations": ["Exact retained initialized objects only, no constructor/load/free/appointment transitions",
            "Fresh sparse input excluded: missing player table extents/globals",
            "Two chosen reciprocal candidate members; seven anomalous list entries not admitted",
            "Only slot zero and ordinary mode zero; no cache invalidation, duplicate removal or swap",
            "Full retained heap and loaded official PE checked; not original-process or original-save equivalence",
            "Original unsupported diagnostic paths remain censored, not rejection parity"]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("binary", type=Path); p.add_argument("capture", type=Path); p.add_argument("output", type=Path)
    a = p.parse_args()
    timing = a.output.with_suffix(a.output.suffix+".timing.json")
    require(not a.output.exists() and not timing.exists(), "output exists")
    attempts = []
    started = time.monotonic()
    with a.output.open("x", encoding="utf8") as stream, timing.open("x", encoding="utf8") as timer:
        try:
            receipt = generate(a.binary, a.capture, attempts)
        except Exception as error:
            receipt = {"status": "failed", "error_type": type(error).__name__, "attempts": attempts,
                       "production_admission": "none", "comparison_verdict": "not-comparable"}
            stream.write(json.dumps(receipt, indent=2)+"\n")
            raise SystemExit("failed; sanitized attempt retained") from None
        else:
            stream.write(json.dumps(receipt, indent=2)+"\n")
        finally:
            timer.write(json.dumps({"elapsed_seconds": time.monotonic()-started, "attempts": attempts}, indent=2)+"\n")
    print(json.dumps({"successful_calls": receipt["successful_calls"], "receipt_sha256": digest(a.output.read_bytes())}))
