#!/usr/bin/env python3
"""Private bounded PC-R5 build/capture driver. Never launches a Windows process."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import selectors
import shlex
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True

PIN = "144ed82c248228c7769c6785899527eae5b33c3d"
BASELINE = "9a41f4a028f0dd1df71e3f9f18f9821a17f91947bb20e7ed0ba9fc18fcafa07b"
SPECIMEN = "0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86"
CLEAN = "920cbf75653473d276cd33fbbe7a90553dcd6fff4c0878e848aaca7736dddac6"
SMOKE = "3428aeae65a2dcd899e123b8c9649d109404cd11c601d2c89947d872d8d7196b"
def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":")).encode()
def identity(p):
    p = Path(p)
    if p.is_symlink() or not p.is_file():
        raise ValueError("nonregular/symlink input")
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return {"bytes": p.stat().st_size, "sha256": h.hexdigest()}
def write(p, v):
    with p.open("xb") as f:
        f.write(canonical(v)+b"\n")
def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
def source_identity(source):
    if git(source, "rev-parse", "HEAD") != PIN or git(source, "status", "--porcelain"):
        raise ValueError("wrong or modified Bosman source")
    return {"revision": PIN, "tree": git(source, "rev-parse", "HEAD^{tree}")}
def clean_identity(game, manifest):
    if identity(manifest)["sha256"] != CLEAN:
        raise ValueError("wrong manifest")
    expected = set()
    for line in manifest.read_text().splitlines():
        if line.startswith("#"):
            continue
        sha, count, rel = line.split("\t")
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts or "\\" in rel or rel in expected:
            raise ValueError("unsafe clean path")
        expected.add(rel)
        if any(parent.is_symlink() for parent in [game/p, *(game/p).parents]):
            raise ValueError("symlink in clean input")
        if identity(game/p) != {"bytes": int(count), "sha256": sha}:
            raise ValueError("clean identity mismatch")
    actual = {p.relative_to(game).as_posix() for p in game.rglob("*") if p.is_file()}
    if len(expected) != 760 or actual != expected:
        raise ValueError("clean inventory mismatch")
    if identity(game/"cm0102.exe")["sha256"] != SPECIMEN:
        raise ValueError("wrong specimen")
    return {"manifest": identity(manifest), "file_count": len(expected),
            "specimen": identity(game/"cm0102.exe")}
def newdir(p):
    p.mkdir(mode=0o700)
def build(a):
    source_identity(a.source)
    if identity(a.build/"cm0102_recomp")["sha256"] != BASELINE:
        raise ValueError("qualified binary changed")
    newdir(a.output)
    a.admitted = True
    observer = Path(__file__).with_name("pc_r5_observer.c")
    commands = subprocess.check_output(["ninja", "-t", "commands", "cm0102_recomp"],
                                      cwd=a.build, text=True).splitlines()
    # Select the existing final native link only; never run generators/build graph.
    link = next(c for c in reversed(commands) if " -o cm0102_recomp " in c)
    link = link.removeprefix(": && ").removesuffix(" && :")
    argv = shlex.split(link)
    if any(x in argv for x in ["&&", ";", "|"]) or argv[0] != "/usr/bin/cc":
        raise ValueError("unsupported link recipe")
    objects = [x for x in argv if x.endswith(".o")]
    inputs = {x: identity(a.build/x) for x in objects}
    compile_cmd = ["/usr/bin/cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                   "-I"+str(a.source/"src/recomp_rt"), "-c", str(observer),
                   "-o", str(a.output/"observer.o")]
    link_cmd = list(argv)
    link_cmd[link_cmd.index("-o")+1] = str(a.output/"cm0102_observed")
    link_cmd += [str(a.output/"observer.o"), "-Wl,--wrap=f_005cde40"]
    receipt = {"sealed_unix_time_ns": time.time_ns(), "schema_version": 1, "source": source_identity(a.source),
               "source_patch": "none; separate linker observer",
               "headers": {h: identity(a.source/"src/recomp_rt"/h) for h in ["rt.h", "rt_host.h"]},
               "observer": identity(observer), "baseline": identity(a.build/"cm0102_recomp"),
               "build_inputs": inputs, "build_ninja": identity(a.build/"build.ninja"),
               "cmake_cache": identity(a.build/"CMakeCache.txt"),
               "compiler": identity(Path("/usr/bin/cc").resolve()),
               "tool_files": {t: identity(Path(t).resolve()) for t in ["/usr/bin/cc","/usr/bin/ld","/usr/bin/ninja"]},
               "compile_command": compile_cmd, "link_command": link_cmd,
               "tools": {t: subprocess.check_output([t, "--version"], text=True).splitlines()[0]
                         for t in ["/usr/bin/cc", "/usr/bin/ld", "/usr/bin/ninja"]}}
    write(a.output/"build-before.json", receipt)
    subprocess.run(compile_cmd, check=True, timeout=60)
    subprocess.run(link_cmd, cwd=a.build, check=True, timeout=120)
    if inputs != {x: identity(a.build/x) for x in objects}:
        raise ValueError("object drift")
    source_identity(a.source)
    receipt["completed_unix_time_ns"] = time.time_ns()
    receipt["instrumented"] = identity(a.output/"cm0102_observed")
    receipt["object"] = identity(a.output/"observer.o")
    write(a.output/"build-receipt.json", receipt)
def parse_capture(p):
    if p.stat().st_size > 16778000:
        raise ValueError("capture oversized")
    data = p.read_bytes()
    if len(data) > 16778000 or data[:8] != b"PCR5SP01" or data[-8:] != b"PCR5DONE":
        raise ValueError("capture incomplete")
    pos, regions = 8, []
    while pos < len(data)-8:
        if pos+8 > len(data)-8:
            raise ValueError("truncated header")
        addr, size = struct.unpack_from("<II", data, pos)
        pos += 8
        if not size or size > 8388608 or addr+size > 2**32 or pos+size > len(data)-8:
            raise ValueError("invalid range")
        if any(addr < base+len(raw) and base < addr+size for base, raw in regions):
            raise ValueError("overlapping/duplicate range")
        regions.append((addr, data[pos:pos+size]))
        pos += size
    globals_ = [0xae235c,0xae2350,0xae2364,0xae23b4,0xae23bc,0xde1d08,0xb63c98,0xae2c90]
    if pos != len(data)-8 or len(regions) != 16:
        raise ValueError("capture range count")
    if [(a,len(b)) for a,b in regions[:8]] != [(a,4) for a in globals_]:
        raise ValueError("wrong global set")
    def read(addr, size):
        for start, raw in regions:
            if start <= addr and addr+size <= start+len(raw):
                return raw[addr-start:addr-start+size]
        raise ValueError("unsupported pointer")
    def u32(addr):
        return struct.unpack("<I", read(addr, 4))[0]
    nc, ns, nations = u32(0xae235c), u32(0xae2364), u32(0xae2350)
    if not 1 <= nc <= 10000 or not 16 <= ns <= 100000 or nations > nc//2:
        raise ValueError("invalid dimensions")
    cb, sb, ctx, reg = [u32(a) for a in globals_[3:7]]
    if [(a,len(b)) for a,b in regions[8:11]] != [(cb,nc*581),(sb,ns*110),(ctx,0x605)]:
        raise ValueError("wrong club/staff/context extent")
    first,nf,second,nb,mapping = [u32(ctx+x) for x in [0x5f9,0x5fd,0x5f1,0x5f5,0x601]]
    if not 1 <= nf <= 256 or not 1 <= nb <= 256:
        raise ValueError("invalid bank counts")
    if [(a,len(b)) for a,b in regions[11:15]] != [
        (mapping,(nc+32)*0x91),(first,nf*6371),(second,nb*6371),(reg,8)]:
        raise ValueError("wrong mapping/bank/registry extent")
    rows, nr = u32(reg), u32(reg+4)
    if not 1 <= nr <= 16 or (regions[15][0],len(regions[15][1])) != (rows,nr*0xa6ef):
        raise ValueError("wrong registry rows")
    if any(not 0x70000000 <= a < a+len(b) <= 0xef000000 for a,b in regions[8:]):
        raise ValueError("unsupported heap pointer")
    humans = []
    for i in range(nc-2*nations):
        club = cb+i*581
        if u32(club) != i:
            raise ValueError("club row identity")
        manager = u32(club+0xcf)
        if sb <= manager < sb+ns*110 and (manager-sb)%110 == 0:
            mid = u32(manager)
            if mid != (manager-sb)//110:
                raise ValueError("manager row identity")
            if mid >= ns-16 and u32(manager+0x39) == club:
                humans.append({"club_address": club, "manager_address": manager, "manager_id": mid})
    if not humans or nr != 16:
        raise ValueError("no reciprocal human input")
    return {"range_count": len(regions), "bytes": sum(len(x) for _, x in regions),
            "human_bindings": humans, "registry_count": nr,
            "regions": [{"address": x, "bytes": len(y), "sha256": hashlib.sha256(y).hexdigest()}
                        for x, y in regions]}
def limits():
    resource.setrlimit(resource.RLIMIT_AS, (6*1024**3, 6*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64*1024**2, 64*1024**2))
def bounded(argv, env, cwd, timeout=240):
    start = time.monotonic()
    buffers = [bytearray(), bytearray()]
    reason = None
    with subprocess.Popen(argv, env=env, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=True, preexec_fn=limits, pass_fds=(int(argv[0].rsplit("/",1)[1]),)) as p:
        sel = selectors.DefaultSelector()
        sel.register(p.stdout, selectors.EVENT_READ, 0)
        sel.register(p.stderr, selectors.EVENT_READ, 1)
        while sel.get_map():
            if time.monotonic()-start > timeout:
                reason = "timeout"
            if reason:
                break
            for key, _ in sel.select(.1):
                b = os.read(key.fd, 65536)
                if not b:
                    sel.unregister(key.fileobj)
                    continue
                buf = buffers[key.data]
                room = 1048576-len(buf)
                buf.extend(b[:room])
                if len(b) > room:
                    reason = "output-limit"
        if reason is None:
            try:
                p.wait(timeout=max(.001, timeout-(time.monotonic()-start)))
            except subprocess.TimeoutExpired:
                reason = "timeout"
        # Kill the group even when its leader already exited, containing any
        # descendants retaining streams. This is not general subreaper fencing.
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.wait(timeout=5)
        sel.close()
        return p.returncode, [bytes(x) for x in buffers], reason, time.monotonic()-start
def runtime_seal(a):
    return {"inputs": clean_identity(a.game,a.manifest), "source": source_identity(a.source),
            "observer": identity(Path(__file__).with_name("pc_r5_observer.c")),
            "driver": identity(__file__), "baseline": identity(a.baseline),
            "instrumented": identity(a.observed/"cm0102_observed"),
            "build_receipt": identity(a.observed/"build-receipt.json"),
            "tools": {x: identity(Path(x).resolve()) for x in
                      [sys.executable,"/usr/bin/cc","/usr/bin/ld","/usr/bin/ninja"]}}
def run(a):
    build_receipt = json.loads((a.observed/"build-receipt.json").read_bytes())
    exe = a.observed/"cm0102_observed"
    if identity(exe) != build_receipt["instrumented"]:
        raise ValueError("instrumented identity mismatch")
    if identity(Path(__file__).with_name("pc_r5_observer.c")) != build_receipt["observer"]:
        raise ValueError("observer revision mismatch")
    source_identity(a.source)
    smoke = a.source/"tests/smoke/smoke_run.py"
    if identity(smoke)["sha256"] != SMOKE:
        raise ValueError("smoke identity mismatch")
    inputs = clean_identity(a.game, a.manifest)
    if identity(a.baseline)["sha256"] != BASELINE:
        raise ValueError("baseline identity mismatch")
    newdir(a.output)
    a.admitted = True
    spec = importlib.util.spec_from_file_location("pinned_smoke", smoke)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Same-save's documented steps, omitting screenshots only, in all arms.
    steps = module.without_intro_click([x for x in module.STEPS
                                      if "dump" not in x and "quit" not in x])+["400000 quit"]
    script = "; ".join(module.scaled_steps("classic", "", steps))
    before = {"sealed_unix_time_ns": time.time_ns(), "source": source_identity(a.source), "inputs": inputs,
              "build_receipt": identity(a.observed/"build-receipt.json"),
              "driver": identity(__file__), "python": identity(Path(sys.executable).resolve()),
              "smoke": identity(smoke), "script_sha256": hashlib.sha256(script.encode()).hexdigest(),
              "script": script, "clock": "RECOMP_FIXED_CLOCK=1", "seed": 1,
              "limits": {"seconds": 240, "cpu_seconds": 300, "as_bytes": 6*1024**3,
                         "file_bytes": 64*1024**2, "each_output_bytes": 1048576},
              "clean_data_consumption_proven": "unknown",
              "consumption_limit": "Explicit --game locator; executable held open. Data opens not independently observed."}
    initial_seal = runtime_seal(a)
    before["runtime_seal"] = initial_seal
    write(a.output/"before.json", before)
    results = []
    for name, program, enabled in [("baseline", a.baseline, False),
                                    ("disabled", exe, False), ("enabled-a", exe, True), ("enabled-b", exe, True)]:
        work = a.output/name
        newdir(work)
        for d in ["home", "user"]:
            newdir(work/d)
        (work/"user/settings.txt").write_text("display = classic\nfaster_days = off\n")
        env = {"PATH": "/usr/bin:/bin", "HOME": str(work/"home"),
               "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy", "RECOMP_NO_BOX": "1",
               "RECOMP_USER_DIR": str(work/"user"), "RECOMP_FIXED_CLOCK": "1",
               "RECOMP_SAVE_AFTER_DAYS": "14", "RECOMP_IDLE_COUNT": "1", "RECOMP_SCRIPT": script}
        if enabled:
            env["PC_R5_CAPTURE"] = str(work/"capture.bin")
        arm_seal = runtime_seal(a)
        write(work/"seal-before.json", {"sealed_unix_time_ns": time.time_ns(), "identity": arm_seal})
        if arm_seal != initial_seal:
            raise ValueError("pre-arm drift")
        with program.open("rb") as handle:
            # The exact same descriptor is hashed and executed.
            held = hashlib.file_digest(handle, "sha256").hexdigest()
            expected = BASELINE if name == "baseline" else build_receipt["instrumented"]["sha256"]
            if held != expected:
                raise ValueError("held executable mismatch")
            argv = ["/proc/self/fd/"+str(handle.fileno()), "--game", str(a.game), "-seed", "1"]
            write(work/"command.json", {"argv": argv, "environment": env, "held_sha256": held})
            code, streams, reason, elapsed = bounded(argv, env, work)
        for filename, raw in zip(["stdout.log", "stderr.log"], streams):
            (work/filename).write_bytes(raw)
        save = work/"user/samesave.sav"
        endpoint = code == 0 and reason is None and save.is_file() and re.search(
            rb"recomp: saved .* after 14 game days", streams[1]) is not None
        record = {"arm": name, "exit_code": code, "elapsed_seconds": elapsed,
                  "execution_status": "succeeded" if endpoint else "failed",
                  "reason": reason or ("completed-target" if endpoint else "missing-endpoint"),
                  "comparison_verdict": "not-run", "capture_status": "disabled"}
        if save.is_file():
            record["save"] = identity(save)
        if enabled:
            try:
                record["capture"] = identity(work/"capture.bin")
                structure = parse_capture(work/"capture.bin")
                write(work/"structure-private.json", structure)
                record["capture_status"] = "complete"
            except (ValueError, OSError):
                record["capture_status"] = "incomplete"
        arm_after = runtime_seal(a)
        write(work/"seal-after.json", {"sealed_unix_time_ns": time.time_ns(), "identity": arm_after})
        record["identities_stable"] = arm_after == initial_seal
        if not record["identities_stable"]:
            record["execution_status"] = "failed"
            record["reason"] = "identity-drift"
        write(work/"result.json", record)
        results.append(record)
    try:
        after = clean_identity(a.game, a.manifest)
        stable = inputs == after and runtime_seal(a) == initial_seal
    except (ValueError, OSError):
        stable = False
    write(a.output/"after.json", {"inputs_stable": stable, "sealed_unix_time_ns": time.time_ns()})
    success = stable and all(r["execution_status"] == "succeeded" for r in results)
    saves_equal = success and len({r["save"]["sha256"] for r in results}) == 1
    captures = [r for r in results if r["arm"].startswith("enabled")]
    captures_complete = all(r["capture_status"] == "complete" for r in captures)
    raw_equal = captures_complete and captures[0]["capture"] == captures[1]["capture"]
    report = {"schema_version": 1, "execution_status": "succeeded" if success else "failed",
              "comparison_verdict": "not-run", "results": results, "inputs_stable": stable,
              "four_arm_saves_equal": saves_equal, "capture_complete": captures_complete,
              "capture_raw_equal": raw_equal, "clean_data_consumption_proven": "unknown",
              "original_process_parity": "not-claimed"}
    report["artifacts"] = {p.relative_to(a.output).as_posix(): identity(p)
                           for p in sorted(a.output.rglob("*")) if p.is_file()}
    write(a.output/"receipt-private.json", report)
    print(json.dumps({k:v for k,v in report.items() if k != "results"}, sort_keys=True))
    return 0 if success and saves_equal and captures_complete and raw_equal else 1
def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    r = sub.add_parser("run")
    for s in [b, r]:
        s.add_argument("--source", type=Path, required=True)
        s.add_argument("--output", type=Path, required=True)
    b.add_argument("--build", type=Path, required=True)
    for flag in ["observed", "game", "manifest", "baseline"]:
        r.add_argument("--"+flag, type=Path, required=True)
    a = p.parse_args()
    for key, value in vars(a).items():
        if isinstance(value, Path) and not value.is_absolute():
            p.error(key+" must be absolute")
    a.admitted = False
    try:
        if a.command == "build":
            build(a)
            return 0
        return run(a)
    except Exception as error:
        if a.admitted:
            write(a.output/"failed.json", {"execution_status": "failed",
                  "reason": "driver-"+type(error).__name__,
                  "comparison_verdict": "not-run", "capture_status": "unknown"})
        print("pc-r5 failed: "+type(error).__name__, file=sys.stderr)
        return 1
if __name__ == "__main__":
    sys.exit(main())
