#!/usr/bin/env python3
"""Actual bounded systemd acceptance. Synthetic engineering controls, no fidelity gate."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import core
import workloads

REPO = Path(__file__).resolve().parents[2]


def run(*args, check=True):
    return subprocess.run(args, check=check, text=True, capture_output=True)


def wait(predicate, seconds=60):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(.1)
    raise RuntimeError("bounded acceptance wait exceeded")


def alive_identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except FileNotFoundError:
        return None


class Qualification:
    def __init__(self, root):
        self.root = root
        self.config = {"python": "/usr/bin/python3"}
        core.atomic_json(root / "config.json", self.config)
        self.units = []
        self.evidence = {"source_revision": run("git", "-C", str(REPO), "rev-parse", "HEAD").stdout.strip(), "source_sha256": {name: core.digest(REPO/"tools/lab"/name) for name in ("core.py", "workloads.py", "qualify_service.py")}, "kernel": os.uname().release, "systemd_version": run("systemd", "--version").stdout.splitlines()[0], "schema_version": 1, "scope": "synthetic systemd engineering acceptance; no phase/fidelity promotion", "started": time.time(), "cases": []}

    def manifest(self, cid, parameters=None, limits=None, jobs=None):
        manifest = workloads.build_profile("synthetic", self.config, REPO, cid)
        manifest["jobs"][0]["job_id"] = "fixture"
        manifest["jobs"][0]["parameters"] = parameters or {"steps": 2, "delay_ms": 10}
        manifest["limits"].update(elapsed_seconds=30, stall_seconds=3, max_attempts=2)
        if limits:
            manifest["limits"].update(limits)
        if jobs:
            manifest["jobs"] = jobs
            manifest["limits"]["max_jobs"] = len(jobs)
        manifest["stop_conditions"]["max_failures"] = 10
        return manifest

    def launch(self, manifest, root=None):
        root = root or self.root
        core.configure(root, REPO, manifest)
        unit = "cm0102-acceptance-" + uuid.uuid4().hex[:12] + ".service"
        self.units.append(unit)
        run("systemd-run", "--user", "--unit="+unit, "--collect",
            "--property=CPUQuota=100%", "--property=MemoryMax=2147483648",
            "--property=MemorySwapMax=0", "--property=TasksMax=128",
            "--property=KillMode=control-group", "--property=SendSIGKILL=yes",
            "--property=Restart=on-failure", "--property=RestartSec=1",
            "--property=RestartPreventExitStatus=2", "--property=TimeoutStopSec=5",
            "--property=UMask=0077", "/usr/bin/python3", str(REPO/"tools/lab/core.py"),
            "--root", str(root), "--repo", str(REPO), "start", manifest["campaign_id"])
        return unit

    def active(self, unit):
        return run("systemctl", "--user", "is-active", "--quiet", unit, check=False).returncode == 0

    def completed(self, cid, unit):
        wait(lambda: core.snapshot(self.root, cid)["campaign"]["state"] in ("completed", "stopped"))
        wait(lambda: not self.active(unit), seconds=15)
        return core.snapshot(self.root, cid)

    def record(self, name, snapshot, **details):
        record = {"case": name, "campaign_id": snapshot["campaign"]["campaign_id"], "campaign_state": snapshot["campaign"]["state"],
                  "jobs": [{key: job[key] for key in ("job_id", "state", "attempts", "comparison_verdict")} for job in snapshot["jobs"]],
                  "attempts": [{key: attempt[key] for key in ("attempt_id", "ordinal", "execution_status", "reason", "publication_state")} for attempt in snapshot["attempts"]], **details}
        self.evidence["cases"].append(record)
        core.atomic_json(self.root/"service-acceptance.json", self.evidence)

    def recovery(self):
        manifest = self.manifest("service-recovery")
        quick = dict(manifest["jobs"][0], job_id="completed-first", parameters={"steps": 2, "delay_ms": 10})
        slow = dict(manifest["jobs"][0], job_id="interrupted-second", parameters={"steps": 80, "delay_ms": 100})
        manifest["jobs"] = [quick, slow]
        manifest["limits"]["max_jobs"] = 2
        unit = self.launch(manifest)
        wait(lambda: len(core.snapshot(self.root, "service-recovery")["attempts"]) == 2)
        initial = core.snapshot(self.root, "service-recovery")
        wait(lambda: (Path(initial["attempts"][1]["directory"])/"progress.json").exists())
        wait(lambda: json.loads((Path(initial["attempts"][1]["directory"])/"progress.json").read_text())["sequence"] >= 2)
        group = run("systemctl", "--user", "show", "--property=ControlGroup", "--value", unit).stdout.strip()
        old_pids = {int(pid): alive_identity(int(pid)) for pid in (Path("/sys/fs/cgroup")/group.lstrip("/")/"cgroup.procs").read_text().split()}
        competing = self.root/"competing-root"
        core.atomic_json(competing/"config.json", self.config)
        probe = self.manifest("competing-root")
        competing_unit = self.launch(probe, root=competing)
        wait(lambda: "execution slot busy" in run("journalctl", "--user", "-u", competing_unit, "--no-pager", "-n", "30").stdout, seconds=10)
        wait(lambda: not self.active(competing_unit), seconds=10)
        if core.snapshot(competing, "competing-root")["attempts"]:
            raise AssertionError("competing state root acquired global execution slot")
        run("systemctl", "--user", "kill", "--kill-whom=main", "--signal=SIGKILL", unit)
        data = self.completed("service-recovery", unit)
        assert [job["state"] for job in data["jobs"]] == ["succeeded", "succeeded"]
        assert [job["attempts"] for job in data["jobs"]] == [1, 2]
        assert data["attempts"][1]["reason"] == "worker-interrupted"
        assert data["attempts"][1]["result"]["details"]["artifacts"]
        assert all(alive_identity(pid) != identity for pid, identity in old_pids.items() if identity is not None)
        assert data["attempts"][0]["attempt_id"] == initial["attempts"][0]["attempt_id"]
        assert all(attempt["publication_state"] == "published" for attempt in data["attempts"])
        samples = [attempt["result"]["details"].get("resources_after") for attempt in data["attempts"]]
        assert any(sample and "cpu.stat" in sample and "memory.peak" in sample for sample in samples)
        self.record("systemd-kill-restart-and-cross-root-exclusion", data, killed_processes=old_pids, resource_samples=samples)
        replay_id = core.replay(self.root, REPO, "service-recovery", "completed-first")
        replay_manifest = core.snapshot(self.root, replay_id)["campaign"]["manifest"]
        replay_unit = self.launch(replay_manifest)
        replayed = self.completed(replay_id, replay_unit)
        assert replayed["jobs"][0]["state"] == "succeeded"
        assert replayed["campaign"]["manifest"]["observation_seconds"] == 0
        self.record("selected-result-replay", replayed)

    def limits(self):
        controls = [("output", {"mode": "output"}, {"output_bytes": 65536}, "output-limit"),
                    ("stall", {"mode": "stall"}, {"stall_seconds": .4}, "semantic-progress-stalled"),
                    ("elapsed", {"mode": "stall"}, {"elapsed_seconds": .4}, "elapsed-limit"),
                    ("disk", {"steps": 50, "delay_ms": 100}, {"disk_bytes": 64}, "disk-limit")]
        for name, parameters, limits, reason in controls:
            cid = "service-"+name
            unit = self.launch(self.manifest(cid, parameters, limits))
            data = self.completed(cid, unit)
            assert len(data["attempts"]) == 1
            assert data["attempts"][0]["reason"] == reason, data["attempts"]
            assert data["jobs"][0]["state"] == "failed"
            self.record("bounded-"+name, data)
        manifest = self.manifest("service-cancel", {"mode": "child-orphan"})
        unit = self.launch(manifest)
        wait(lambda: core.snapshot(self.root, "service-cancel")["attempts"])
        data = core.snapshot(self.root, "service-cancel")
        wait(lambda: (Path(data["attempts"][0]["directory"])/"progress.json").exists())
        time.sleep(.2)
        group = run("systemctl", "--user", "show", "--property=ControlGroup", "--value", unit).stdout.strip()
        before = {int(pid): alive_identity(int(pid)) for pid in (Path("/sys/fs/cgroup")/group.lstrip("/")/"cgroup.procs").read_text().split()}
        core.control(self.root, "service-cancel", "stop")
        data = self.completed("service-cancel", unit)
        assert data["jobs"][0]["state"] == "cancelled"
        assert all(alive_identity(pid) != identity for pid, identity in before.items() if identity is not None)
        assert data["attempts"][0]["result"]["details"]["original_reason"] == "cancelled"
        self.record("cancellation-descendant-cleanup", data, terminated_processes=before)

    def publication_failure(self):
        manifest = self.manifest("service-publication", {"steps": 20, "delay_ms": 100})
        unit = self.launch(manifest)
        wait(lambda: core.snapshot(self.root, "service-publication")["attempts"])
        original = core.snapshot(self.root, "service-publication")["attempts"][0]
        attempt = Path(original["directory"])
        wait(lambda: (attempt/"progress.json").exists())
        obstruction = attempt/"result.json"
        obstruction.mkdir()  # Real filesystem publication error; immutable workload is unchanged.
        data = self.completed("service-publication", unit)
        assert data["jobs"][0]["state"] == "succeeded"
        assert data["attempts"][0]["publication_state"] == "pending"
        assert any(event["kind"] == "publication-failed" for event in data["events"])
        obstruction.rmdir()  # Only the deliberately-created empty directory is removed.
        unit = self.launch(manifest)
        data = self.completed("service-publication", unit)
        assert len(data["attempts"]) == 1
        assert data["attempts"][0]["attempt_id"] == original["attempt_id"]
        assert data["attempts"][0]["publication_state"] == "published"
        assert obstruction.is_file()
        self.record("real-publication-failure-and-reconciliation", data)

    def execute(self):
        try:
            self.recovery()
            self.limits()
            self.publication_failure()
            self.evidence.update(finished=time.time(), outcome="passed")
        except BaseException as error:
            self.evidence.update(finished=time.time(), outcome="failed", error=repr(error))
            raise
        finally:
            for unit in self.units:
                run("systemctl", "--user", "stop", unit, check=False)
            core.atomic_json(self.root/"service-acceptance.json", self.evidence)
        return self.evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="New private evidence directory; never reused")
    args = parser.parse_args()
    root = args.root.resolve()
    if root.exists():
        raise ValueError("acceptance root must not already exist")
    root.mkdir(mode=0o700, parents=True)
    os.umask(0o077)
    result = Qualification(root).execute()
    print(json.dumps({"outcome": result["outcome"], "cases": len(result["cases"]), "evidence": str(root/"service-acceptance.json")}))


if __name__ == "__main__":
    main()
