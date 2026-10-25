"""Durable, single-worker local research queue (Linux, Python standard library)."""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import fcntl
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import uuid

VERDICTS = {"not-run", "equal", "different", "inconclusive", "not-comparable"}
TERMINAL = {"succeeded", "failed", "cancelled", "rejected"}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
DEFAULT_LIMITS = {
    "max_jobs": 1000, "elapsed_seconds": 3600, "stall_seconds": 120,
    "output_bytes": 16 * 1024 * 1024, "disk_bytes": 512 * 1024 * 1024,
    "min_free_bytes": 1024 * 1024 * 1024, "max_attempts": 2,
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + ".pending-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


def connect(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(root / "lab.sqlite3", timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS campaigns(
        campaign_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_sha256 TEXT NOT NULL,
        state TEXT NOT NULL, created REAL NOT NULL, stop_reason TEXT,
        observation_started REAL, active_seconds REAL NOT NULL DEFAULT 0,
        idle_seconds REAL NOT NULL DEFAULT 0, observation_boot_id TEXT,
        observation_start_monotonic REAL, observation_elapsed_seconds REAL NOT NULL DEFAULT 0,
        observation_last_tick REAL, observation_qualified INTEGER NOT NULL DEFAULT 1);
      CREATE TABLE IF NOT EXISTS jobs(
        campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id), job_id TEXT NOT NULL,
        spec TEXT NOT NULL, state TEXT NOT NULL, token INTEGER NOT NULL DEFAULT 0,
        attempts INTEGER NOT NULL DEFAULT 0, execution_status TEXT NOT NULL DEFAULT 'not-run',
        comparison_verdict TEXT NOT NULL DEFAULT 'not-run', reason TEXT,
        PRIMARY KEY(campaign_id,job_id));
      CREATE TABLE IF NOT EXISTS attempts(
        attempt_id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, job_id TEXT NOT NULL,
        ordinal INTEGER NOT NULL, token INTEGER NOT NULL, directory TEXT NOT NULL UNIQUE,
        started REAL NOT NULL, finished REAL, execution_status TEXT NOT NULL DEFAULT 'running',
        comparison_verdict TEXT NOT NULL DEFAULT 'not-run', reason TEXT, result TEXT,
        publication_state TEXT NOT NULL DEFAULT 'pending',
        FOREIGN KEY(campaign_id,job_id) REFERENCES jobs(campaign_id,job_id));
      CREATE TABLE IF NOT EXISTS events(
        sequence INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id TEXT, job_id TEXT,
        attempt_id TEXT, time REAL NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
      CREATE TRIGGER IF NOT EXISTS attempts_identity_immutable BEFORE UPDATE ON attempts
      WHEN NEW.attempt_id != OLD.attempt_id OR NEW.campaign_id != OLD.campaign_id
        OR NEW.job_id != OLD.job_id OR NEW.ordinal != OLD.ordinal OR NEW.token != OLD.token
        OR NEW.directory != OLD.directory OR NEW.started != OLD.started
      BEGIN SELECT RAISE(ABORT,'attempt identity is immutable'); END;
      CREATE TRIGGER IF NOT EXISTS attempts_terminal_immutable BEFORE UPDATE ON attempts
      WHEN OLD.finished IS NOT NULL AND (NEW.execution_status != OLD.execution_status
        OR NEW.comparison_verdict != OLD.comparison_verdict OR NEW.result IS NOT OLD.result
        OR NEW.reason IS NOT OLD.reason OR NEW.finished IS NOT OLD.finished)
      BEGIN SELECT RAISE(ABORT,'terminal attempt is immutable'); END;
    """)
    # Initial local-v1 development databases are recoverable without deleting evidence.
    fields = {row[1] for row in db.execute("PRAGMA table_info(campaigns)")}
    for name, declaration in {
        "observation_started": "REAL", "active_seconds": "REAL NOT NULL DEFAULT 0",
        "idle_seconds": "REAL NOT NULL DEFAULT 0", "observation_boot_id": "TEXT",
        "observation_start_monotonic": "REAL", "observation_elapsed_seconds": "REAL NOT NULL DEFAULT 0",
        "observation_last_tick": "REAL", "observation_qualified": "INTEGER NOT NULL DEFAULT 1",
    }.items():
        if name not in fields:
            db.execute("ALTER TABLE campaigns ADD COLUMN " + name + " " + declaration)
    return db


@contextlib.contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        db.execute("ROLLBACK")
        raise
    else:
        db.execute("COMMIT")


def event(db, campaign, kind, detail, job=None, attempt=None):
    db.execute("INSERT INTO events(campaign_id,job_id,attempt_id,time,kind,detail) VALUES(?,?,?,?,?,?)",
               (campaign, job, attempt, time.time(), kind, canonical(detail)))


def load_config(root):
    path = Path(root) / "config.json"
    return json.loads(path.read_text()) if path.exists() else {}


def check_pins(pins, repo):
    if not isinstance(pins, list):
        raise ValueError("pins must be a list")
    for pin in pins:
        if set(pin) != {"path", "sha256"} or not re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]):
            raise ValueError("pin requires path and lowercase sha256")
        path = Path(pin["path"])
        if not path.is_absolute():
            path = Path(repo) / path
        if not path.is_file() or digest(path) != pin["sha256"]:
            raise ValueError("missing or changed pinned file: " + str(path))


def check_global(manifest, repo):
    if manifest.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    if not IDENTIFIER.fullmatch(manifest.get("campaign_id", "")):
        raise ValueError("invalid campaign_id")
    revision = manifest.get("source_revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("full source_revision required")
    actual = subprocess.check_output(["/usr/bin/git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if revision != actual:
        raise ValueError("source revision differs from checkout")
    check_pins(manifest.get("pins"), repo)
    own_path = Path(__file__).resolve()
    if not any((Path(pin["path"]) if Path(pin["path"]).is_absolute() else Path(repo)/pin["path"]).resolve() == own_path for pin in manifest["pins"]):
        raise ValueError("worker core source must be pinned")
    limits = manifest.get("limits", {})
    if set(limits) != set(DEFAULT_LIMITS):
        raise ValueError("all finite resource limits required: " + ",".join(DEFAULT_LIMITS))
    for key, value in limits.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError("invalid positive finite limit: " + key)
    if any(not isinstance(limits[key], int) for key in ("max_jobs", "output_bytes", "disk_bytes", "min_free_bytes", "max_attempts")):
        raise ValueError("count and byte limits must be integers")
    if limits["max_attempts"] > 3 or limits["max_jobs"] > 10000:
        raise ValueError("max_attempts <= 3 and max_jobs <= 10000 required")
    observation = manifest.get("observation_seconds", 0)
    if isinstance(observation, bool) or not isinstance(observation, (int, float)) or not math.isfinite(observation) or observation < 0 or observation > 86400:
        raise ValueError("observation_seconds must be finite between 0 and 86400")
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or not jobs or len(jobs) > limits["max_jobs"]:
        raise ValueError("finite nonempty jobs within max_jobs required")
    stops = manifest.get("stop_conditions", {})
    if not isinstance(stops.get("max_failures"), int) or isinstance(stops.get("max_failures"), bool) or stops["max_failures"] < 1:
        raise ValueError("positive max_failures required")
    if not isinstance(stops.get("stop_on_divergence"), bool):
        raise ValueError("boolean stop_on_divergence required")
    if not isinstance(manifest.get("provenance"), dict):
        raise ValueError("provenance required")


def adapters():
    return importlib.import_module("workloads")


def configure(root, repo, manifest, adapter=None):
    adapter = adapter or adapters()
    check_global(manifest, repo)
    config = load_config(root)
    adapter.validate(manifest, Path(repo), config=config)
    cid = manifest["campaign_id"]
    encoded = canonical(manifest)
    db = connect(root)
    seen = set()
    records = []
    for index, spec in enumerate(manifest["jobs"]):
        jid = spec.get("job_id", "") if isinstance(spec, dict) else ""
        reason = None
        try:
            if not IDENTIFIER.fullmatch(jid) or jid in seen:
                raise ValueError("invalid or duplicate job_id")
            seen.add(jid)
            check_pins(spec.get("pins", []), repo)
            adapter.validate_job(manifest, spec, Path(repo), config=config)
        except (ValueError, OSError, KeyError, TypeError) as error:
            reason = str(error)
            # Even malformed and duplicated jobs get a stable separate denominator row.
            jid = "_rejected-" + str(index) + "-" + hashlib.sha256(canonical(spec).encode()).hexdigest()[:12]
        records.append((jid, canonical(spec), "rejected" if reason else "queued", reason))
    with transaction(db):
        previous = db.execute("SELECT manifest FROM campaigns WHERE campaign_id=?", (cid,)).fetchone()
        if previous:
            if previous[0] != encoded:
                raise ValueError("campaign id already freezes a different manifest")
            return cid
        db.execute("INSERT INTO campaigns(campaign_id,manifest,manifest_sha256,state,created) VALUES(?,?,?,?,?)",
                   (cid, encoded, hashlib.sha256(encoded.encode()).hexdigest(), "ready", time.time()))
        for jid, spec, state, reason in records:
            db.execute("INSERT INTO jobs(campaign_id,job_id,spec,state,reason) VALUES(?,?,?,?,?)", (cid, jid, spec, state, reason))
            event(db, cid, "rejected" if reason else "queued", {"reason": reason}, job=jid)
    atomic_json(Path(root) / "campaigns" / cid / "manifest.json", manifest)
    return cid


def snapshot(root, campaign_id):
    db = connect(root)
    campaign = db.execute("SELECT * FROM campaigns WHERE campaign_id=?", (campaign_id,)).fetchone()
    if not campaign:
        raise ValueError("unknown campaign")
    result = {"campaign": dict(campaign)}
    result["campaign"]["manifest"] = json.loads(campaign["manifest"])
    for table in ("jobs", "attempts", "events"):
        result[table] = [dict(row) for row in db.execute("SELECT * FROM " + table + " WHERE campaign_id=? ORDER BY " + ("sequence" if table == "events" else "rowid"), (campaign_id,))]
    for job in result["jobs"]:
        job["spec"] = json.loads(job["spec"])
    for attempt in result["attempts"]:
        attempt["result"] = json.loads(attempt["result"]) if attempt["result"] else None
    for item in result["events"]:
        item["detail"] = json.loads(item["detail"])
    db.close()
    return result


def control(root, campaign_id, action):
    db = connect(root)
    with transaction(db):
        row = db.execute("SELECT state FROM campaigns WHERE campaign_id=?", (campaign_id,)).fetchone()
        if not row:
            raise ValueError("unknown campaign")
        if action == "stop":
            db.execute("UPDATE campaigns SET state='stopped',stop_reason='operator' WHERE campaign_id=?", (campaign_id,))
            db.execute("UPDATE jobs SET state='cancelled',token=token+1,execution_status='cancelled',reason='operator' WHERE campaign_id=? AND state IN ('queued','running')", (campaign_id,))
        elif action == "resume":
            if row[0] != "stopped":
                raise ValueError("only stopped campaigns can resume")
            reason = db.execute("SELECT stop_reason FROM campaigns WHERE campaign_id=?", (campaign_id,)).fetchone()[0]
            if reason in ("observation-gap", "observation-boot", "artifact-integrity"):
                raise ValueError("censored observation or artifact integrity requires a new campaign")
            db.execute("UPDATE campaigns SET state='ready',stop_reason=NULL WHERE campaign_id=?", (campaign_id,))
            db.execute("UPDATE jobs SET state='queued',reason=NULL WHERE campaign_id=? AND state='cancelled' AND reason='operator'", (campaign_id,))
        else:
            raise ValueError("unknown control")
        event(db, campaign_id, action, {})
    db.close()


def claim(db, root, cid):
    with transaction(db):
        campaign = db.execute("SELECT state FROM campaigns WHERE campaign_id=?", (cid,)).fetchone()
        if not campaign or campaign[0] not in ("ready", "running"):
            return None
        job = db.execute("SELECT * FROM jobs WHERE campaign_id=? AND state='queued' ORDER BY rowid LIMIT 1", (cid,)).fetchone()
        if not job:
            return None
        aid = uuid.uuid4().hex
        token = job["token"] + 1
        directory = str(Path(root).resolve() / "attempts" / aid)
        db.execute("UPDATE jobs SET state='running',token=?,attempts=attempts+1 WHERE campaign_id=? AND job_id=?", (token, cid, job["job_id"]))
        db.execute("UPDATE campaigns SET state='running' WHERE campaign_id=?", (cid,))
        db.execute("INSERT INTO attempts(attempt_id,campaign_id,job_id,ordinal,token,directory,started) VALUES(?,?,?,?,?,?,?)", (aid, cid, job["job_id"], job["attempts"] + 1, token, directory, time.time()))
        event(db, cid, "claimed", {"token": token}, job["job_id"], aid)
    return dict(db.execute("SELECT * FROM attempts WHERE attempt_id=?", (aid,)).fetchone())


def finish(db, attempt, result, max_attempts):
    status = result["execution_status"]
    verdict = result.get("comparison_verdict", "not-run")
    if status not in {"succeeded", "failed", "infrastructure_failed", "cancelled", "rejected"} or verdict not in VERDICTS:
        raise ValueError("invalid adapter result classification")
    with transaction(db):
        row = db.execute("SELECT state,token FROM jobs WHERE campaign_id=? AND job_id=?", (attempt["campaign_id"], attempt["job_id"])).fetchone()
        active = row["state"] == "running" and row["token"] == attempt["token"]
        terminal = db.execute("SELECT finished FROM attempts WHERE attempt_id=?", (attempt["attempt_id"],)).fetchone()[0]
        if terminal is not None:
            return False
        if not active:
            result = {"execution_status": "cancelled", "comparison_verdict": "not-run", "reason": "fenced-stale-publication", "details": {**result.get("details", {}), "discarded_status": status, "original_reason": result.get("reason")}}
            status, verdict = "cancelled", "not-run"
        db.execute("UPDATE attempts SET finished=?,execution_status=?,comparison_verdict=?,reason=?,result=? WHERE attempt_id=? AND finished IS NULL", (time.time(), status, verdict, result.get("reason"), canonical(result), attempt["attempt_id"]))
        if active:
            state = "queued" if status == "infrastructure_failed" and attempt["ordinal"] < max_attempts else ("failed" if status == "infrastructure_failed" else status)
            db.execute("UPDATE jobs SET state=?,execution_status=?,comparison_verdict=?,reason=? WHERE campaign_id=? AND job_id=? AND state='running' AND token=?", (state, status, verdict, result.get("reason"), attempt["campaign_id"], attempt["job_id"], attempt["token"]))
        event(db, attempt["campaign_id"], "finished" if active else "fenced", result, attempt["job_id"], attempt["attempt_id"])
    return active


def artifact_inventory(directory):
    directory = Path(directory)
    inventory = []
    if not directory.exists():
        return inventory
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("attempt artifact symlink is forbidden: " + str(path))
        if not path.is_file() or path.name == "result.json" or ".pending-" in path.name:
            continue
        with path.open("rb") as stream:
            os.fsync(stream.fileno())
        inventory.append({"path": str(path.relative_to(directory)), "sha256": digest(path), "byte_count": path.stat().st_size})
    return inventory


def resource_sample():
    try:
        relative = next(line[3:] for line in Path("/proc/self/cgroup").read_text().splitlines() if line.startswith("0::"))
        directory = Path("/sys/fs/cgroup") / relative.lstrip("/")
        sample = {"cgroup": relative}
        for name in ("cpu.stat", "memory.current", "memory.peak", "memory.events", "pids.current"):
            path = directory / name
            if path.exists():
                sample[name] = path.read_text().strip()
        return sample
    except (OSError, StopIteration):
        return {"unavailable": True}


def reconcile(db, cid, verify_published=False):
    """DB is authoritative; independently retry durable result file publication."""
    query = "SELECT * FROM attempts WHERE campaign_id=? AND finished IS NOT NULL"
    if not verify_published:
        query += " AND publication_state!='published'"
    for row in db.execute(query, (cid,)).fetchall():
        try:
            result = json.loads(row["result"])
            destination = Path(row["directory"]) / "result.json"
            if destination.exists():
                if destination.read_text() != canonical(result)+"\n":
                    raise OSError("immutable result publication differs from durable record")
            elif row["publication_state"] == "published":
                raise OSError("published immutable result is missing")
            else:
                atomic_json(destination, result)
            expected = result.get("details", {}).get("artifacts")
            if expected is not None and artifact_inventory(row["directory"]) != expected:
                raise OSError("immutable attempt artifact inventory differs")
        except (OSError, ValueError) as error:
            if row["publication_state"] in ("published", "corrupt"):
                db.execute("UPDATE attempts SET publication_state='corrupt' WHERE attempt_id=?", (row["attempt_id"],))
                db.execute("UPDATE campaigns SET state='stopped',stop_reason='artifact-integrity' WHERE campaign_id=?", (cid,))
            event(db, cid, "publication-failed", {"error": str(error)}, row["job_id"], row["attempt_id"])
        else:
            db.execute("UPDATE attempts SET publication_state='published' WHERE attempt_id=?", (row["attempt_id"],))


def recover(db, cid, max_attempts):
    """Caller must own global slot after service has killed old descendants."""
    for row in db.execute("SELECT * FROM attempts WHERE campaign_id=? AND finished IS NULL", (cid,)).fetchall():
        attempt = dict(row)
        recovered = {"execution_status": "infrastructure_failed", "comparison_verdict": "not-run", "reason": "worker-interrupted", "details": {"resources": "unavailable: worker died before final sample"}}
        try:
            recovered["details"]["artifacts"] = artifact_inventory(attempt["directory"])
        except (OSError, ValueError) as error:
            recovered.update(execution_status="failed", reason="recovery-artifact-integrity: " + str(error))
        finish(db, attempt, recovered, max_attempts)
        event(db, cid, "recovered", {}, attempt["job_id"], attempt["attempt_id"])
    reconcile(db, cid, verify_published=True)


@contextlib.contextmanager
def lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("execution slot busy: " + str(path)) from error
        yield fd
    finally:
        os.close(fd)


def check_cgroup():
    line = next((line for line in Path("/proc/self/cgroup").read_text().splitlines() if line.startswith("0::")), "")
    relative = line[3:]
    if not relative or not relative.endswith(".service"):
        raise RuntimeError("unattended worker must run in a systemd service cgroup")
    path = Path("/sys/fs/cgroup") / relative.lstrip("/")
    quota, period = (path / "cpu.max").read_text().split()
    memory = (path / "memory.max").read_text().strip()
    tasks = (path / "pids.max").read_text().strip()
    if quota == "max" or int(quota) > int(period) or memory == "max" or int(memory) > 2 * 1024**3 or tasks == "max" or int(tasks) > 128:
        raise RuntimeError("worker cgroup requires CPUQuota<=100%, MemoryMax<=2GiB, TasksMax<=128")
    return {"path": relative, "cpu_max": [quota, period], "memory_max": memory, "pids_max": tasks}


def cgroup_populated(relative):
    path = Path("/sys/fs/cgroup") / relative.lstrip("/") / "cgroup.events"
    try:
        return "populated 1" in path.read_text().splitlines()
    except FileNotFoundError:
        return False


def register_slot_owner(fd, cgroup):
    if cgroup.get("test_only"):
        return
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    lock_path = Path(os.readlink(f"/proc/self/fd/{fd}"))
    owner_path = lock_path.with_name(lock_path.name+".owner.json")
    previous = owner_path.read_bytes() if owner_path.exists() else b""
    if previous:
        try:
            owner = json.loads(previous)
        except ValueError as error:
            raise RuntimeError("invalid global slot ownership record; operator inspection required") from error
        if owner.get("boot_id") == boot and owner.get("cgroup") != cgroup["path"] and cgroup_populated(owner["cgroup"]):
            raise RuntimeError("previous worker cgroup still populated; wait for whole-service cleanup")
    atomic_json(owner_path, {"boot_id": boot, "cgroup": cgroup["path"], "pid": os.getpid()})


def nested_stream_bytes(directory):
    total = 0
    for path in Path(directory).rglob("*"):
        if path.parent == Path(directory) and path.name in ("stdout.log", "stderr.log"):
            continue
        if path.is_symlink():
            continue
        if path.suffix in (".stdout", ".stderr", ".log") or path.name == "stdout.ndjson":
            try:
                total += path.stat().st_size if path.is_file() else 0
            except FileNotFoundError:
                pass
    return total


def tree_bytes(path):
    total = 0
    for directory, _, files in os.walk(path, followlinks=False):
        for name in files:
            file = Path(directory) / name
            if not file.is_symlink():
                try:
                    total += file.stat().st_size
                except FileNotFoundError:
                    pass
    return total


def enable_subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # Linux PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "cannot establish descendant recovery")


def descendants(pid):
    found = set()
    pending = [pid]
    while pending:
        parent = pending.pop()
        try:
            children = Path(f"/proc/{parent}/task/{parent}/children").read_text().split()
        except FileNotFoundError:
            continue
        for child in map(int, children):
            if child not in found:
                found.add(child)
                pending.append(child)
    return found


def signal_descendants(signum):
    # pidfds prevent a PID recycled between discovery and signaling hitting a new process.
    for pid in descendants(os.getpid()):
        try:
            fd = os.pidfd_open(pid)
        except ProcessLookupError:
            continue
        try:
            signal.pidfd_send_signal(fd, signum)
        except ProcessLookupError:
            pass
        finally:
            os.close(fd)


def kill_group(process):
    signal_descendants(signal.SIGTERM)
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    # Descendants may survive even after the immediate child exits.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    signal_descendants(signal.SIGKILL)
    process.wait()
    deadline = time.monotonic()+2
    while time.monotonic() < deadline:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            signal_descendants(signal.SIGKILL)
            time.sleep(.01)


def observation_tick(db, cid):
    row = db.execute("SELECT observation_boot_id,observation_start_monotonic,observation_last_tick,observation_elapsed_seconds,state,manifest FROM campaigns WHERE campaign_id=?", (cid,)).fetchone()
    if row["state"] == "completed":
        return row["observation_elapsed_seconds"]
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    if row["observation_boot_id"] != boot:
        db.execute("UPDATE campaigns SET state='stopped',stop_reason='observation-boot',observation_qualified=0 WHERE campaign_id=?", (cid,))
        event(db, cid, "observation-boot", {"qualification": "censored; boot changed"})
        raise RuntimeError("observation boot changed; preserve interrupted campaign and configure a new observation")
    now = time.monotonic()
    elapsed = max(0, now-row["observation_start_monotonic"])
    if row["observation_last_tick"] is not None and now-row["observation_last_tick"] > 30 and json.loads(row["manifest"]).get("observation_seconds", 0) > 0:
        with transaction(db):
            db.execute("UPDATE campaigns SET state='stopped',stop_reason='observation-gap',observation_qualified=0 WHERE campaign_id=?", (cid,))
            db.execute("UPDATE jobs SET state='cancelled',token=token+1,execution_status='cancelled',reason='observation-gap' WHERE campaign_id=? AND state='running'", (cid,))
            event(db, cid, "observation-gap", {"unobserved_seconds": now-row["observation_last_tick"], "qualification": "censored; configure a new campaign"})
    db.execute("UPDATE campaigns SET observation_elapsed_seconds=?,observation_last_tick=? WHERE campaign_id=?", (elapsed, now, cid))
    return elapsed


def write_report(root, cid):
    try:
        module = importlib.import_module("report")
    except ModuleNotFoundError as error:
        if error.name == "report":
            return
        raise
    try:
        module.write_report(root, cid, snapshot(root, cid))
    except Exception as error:
        db = connect(root)
        event(db, cid, "report-publication-failed", {"error_type": type(error).__name__, "error": str(error)})
        db.close()


def execute(db, attempt, manifest, job, repo, adapter, config, slot_fd):
    directory = Path(attempt["directory"])
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    atomic_json(directory / "request.json", {"attempt_id": attempt["attempt_id"], "token": attempt["token"], "manifest_sha256": hashlib.sha256(canonical(manifest).encode()).hexdigest(), "job": job})
    limits = manifest["limits"]
    try:
        check_global(manifest, repo)
        check_pins(job.get("pins", []), repo)
        adapter.validate_job(manifest, job, Path(repo), config=config)
        prepared = adapter.prepare(manifest, job, directory, Path(repo), config=config)
    except (ValueError, OSError, KeyError, TypeError) as error:
        return {"execution_status": "rejected", "comparison_verdict": "not-run", "reason": "preflight: " + str(error), "details": {}}
    argv = prepared["argv"]
    if not argv or not Path(argv[0]).is_absolute():
        raise ValueError("adapter executable must be absolute")
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "HOME": str(directory), "TMPDIR": str(directory)}
    env.update(prepared.get("env", {}))
    start = last_progress = accounted = time.monotonic()
    progress_sequence = -1
    output = 0
    nested_output = 0
    reason = None
    process = subprocess.Popen(argv, cwd=prepared.get("cwd", str(directory)), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, pass_fds=(slot_fd,))
    selector = selectors.DefaultSelector()
    streams = []
    try:
        for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(pipe.fileno(), False)
            stream = (directory / (name + ".log")).open("xb")
            streams.append(stream)
            selector.register(pipe, selectors.EVENT_READ, stream)
        while True:
            for key, _ in selector.select(timeout=0.05):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                retained = chunk[:max(0, limits["output_bytes"] - output)]
                key.data.write(retained)
                output += len(chunk)
                if output > limits["output_bytes"]:
                    reason = "output-limit"
            now = time.monotonic()
            if now - accounted >= 1:
                if now-accounted <= 30:
                    db.execute("UPDATE campaigns SET active_seconds=active_seconds+? WHERE campaign_id=?", (now-accounted, attempt["campaign_id"]))
                accounted = now
                observation_tick(db, attempt["campaign_id"])
            progress_file = prepared.get("progress_file")
            if progress_file:
                try:
                    if Path(progress_file).stat().st_size > 65536:
                        raise ValueError("progress frame exceeds 64KiB")
                    payload = json.loads(Path(progress_file).read_text())
                    sequence = payload["sequence"]
                    if isinstance(sequence, int) and not isinstance(sequence, bool) and sequence > progress_sequence:
                        progress_sequence = sequence
                        last_progress = now
                except (OSError, ValueError, KeyError, TypeError):
                    pass
            nested_output = nested_stream_bytes(directory)
            if output + nested_output > limits["output_bytes"]:
                reason = "output-limit"
            active = db.execute("SELECT state,token FROM jobs WHERE campaign_id=? AND job_id=?", (attempt["campaign_id"], attempt["job_id"])).fetchone()
            if active["state"] != "running" or active["token"] != attempt["token"]:
                reason = "cancelled"
            elif now - start > limits["elapsed_seconds"]:
                reason = "elapsed-limit"
            elif now - last_progress > limits["stall_seconds"]:
                reason = "semantic-progress-stalled"
            elif tree_bytes(directory) > limits["disk_bytes"]:
                reason = "disk-limit"
            elif shutil.disk_usage(directory).free < limits["min_free_bytes"]:
                reason = "disk-free-floor"
            if reason:
                kill_group(process)
                break
            if process.poll() is not None and not selector.get_map():
                break
        if reason:
            status = "cancelled" if reason == "cancelled" else "failed"
            return {"execution_status": status, "comparison_verdict": "not-run", "reason": reason, "details": {"output_bytes_seen": output, "nested_stream_bytes": nested_output, "progress_sequence": progress_sequence}}
        result = adapter.result(manifest, job, directory, process.returncode)
        result.setdefault("comparison_verdict", "not-run")
        result.setdefault("details", {})
        result["details"]["output_bytes_seen"] = output
        result["details"]["nested_stream_bytes"] = nested_output
        result["details"]["progress_sequence"] = progress_sequence
        return result
    finally:
        duration = time.monotonic()-accounted
        if duration <= 30:
            db.execute("UPDATE campaigns SET active_seconds=active_seconds+? WHERE campaign_id=?", (duration, attempt["campaign_id"]))
        kill_group(process)
        observation_tick(db, attempt["campaign_id"])
        selector.close()
        for stream in streams:
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
        process.stdout.close()
        process.stderr.close()


def stop_policy(db, campaign_id, manifest):
    failures = db.execute("SELECT count(*) FROM jobs WHERE campaign_id=? AND state IN ('failed','rejected')", (campaign_id,)).fetchone()[0]
    divergence = db.execute("SELECT count(*) FROM jobs WHERE campaign_id=? AND comparison_verdict='different'", (campaign_id,)).fetchone()[0]
    if failures >= manifest["stop_conditions"]["max_failures"] or (divergence and manifest["stop_conditions"]["stop_on_divergence"]):
        with transaction(db):
            db.execute("UPDATE campaigns SET state='stopped',stop_reason='stop-condition' WHERE campaign_id=? AND state!='stopped'", (campaign_id,))
            event(db, campaign_id, "stop-condition", {"failures": failures, "divergences": divergence})
        return True
    return False


def run_worker(root, repo, campaign_id, adapter=None, require_cgroup=True, heavy_lock=None):
    adapter = adapter or adapters()
    root, repo = Path(root).resolve(), Path(repo).resolve()
    enable_subreaper()
    cgroup = check_cgroup() if require_cgroup else {"test_only": True}
    global_slot = Path(heavy_lock) if heavy_lock else Path("/run/user") / str(os.getuid()) / "cm0102-lab-heavy.lock"
    with lock(root / "worker.lock"), lock(global_slot) as slot_fd:
        register_slot_owner(slot_fd, cgroup)
        db = connect(root)
        data = snapshot(root, campaign_id)
        manifest = data["campaign"]["manifest"]
        config = load_config(root)
        check_global(manifest, repo)
        adapter.validate(manifest, repo, config=config)
        recover(db, campaign_id, manifest["limits"]["max_attempts"])
        db.execute("UPDATE campaigns SET observation_started=COALESCE(observation_started,?),observation_boot_id=COALESCE(observation_boot_id,?),observation_start_monotonic=COALESCE(observation_start_monotonic,?) WHERE campaign_id=?", (time.time(), Path("/proc/sys/kernel/random/boot_id").read_text().strip(), time.monotonic(), campaign_id))
        observation_tick(db, campaign_id)
        manifest_path = root / "campaigns" / campaign_id / "manifest.json"
        if manifest_path.exists() and manifest_path.read_text() != canonical(manifest)+"\n":
            raise ValueError("durable manifest publication differs from canonical record")
        if not manifest_path.exists():
            atomic_json(manifest_path, manifest)
        event(db, campaign_id, "worker-started", {"cgroup": cgroup, "pid": os.getpid()})
        report_time = 0
        idle_entered = False
        while True:
            if stop_policy(db, campaign_id, manifest):
                break
            attempt = claim(db, root, campaign_id)
            if attempt is None:
                current = db.execute("SELECT state FROM campaigns WHERE campaign_id=?", (campaign_id,)).fetchone()
                elapsed = observation_tick(db, campaign_id)
                horizon = manifest.get("observation_seconds", 0)
                if current["state"] == "stopped" or elapsed >= horizon:
                    break
                if not idle_entered:
                    event(db, campaign_id, "idle-observation", {"remaining_seconds": max(0, horizon-(elapsed))})
                    idle_entered = True
                before = time.monotonic()
                time.sleep(min(1, max(0, horizon-(elapsed))))
                duration = time.monotonic()-before
                if duration <= 30:
                    db.execute("UPDATE campaigns SET idle_seconds=idle_seconds+? WHERE campaign_id=?", (duration, campaign_id))
                observation_tick(db, campaign_id)
                if time.monotonic()-report_time >= 30:
                    write_report(root, campaign_id)
                    report_time = time.monotonic()
                continue
            idle_entered = False
            job = json.loads(db.execute("SELECT spec FROM jobs WHERE campaign_id=? AND job_id=?", (campaign_id, attempt["job_id"])).fetchone()[0])
            before_resources = resource_sample()
            try:
                result = execute(db, attempt, manifest, job, repo, adapter, config, slot_fd)
            except Exception as error:
                result = {"execution_status": "infrastructure_failed", "comparison_verdict": "not-run", "reason": "adapter-infrastructure: " + str(error), "details": {}}
            result.setdefault("details", {})
            result["details"]["resources_before"] = before_resources
            result["details"]["resources_after"] = resource_sample()
            try:
                result["details"]["artifacts"] = artifact_inventory(attempt["directory"])
            except (OSError, ValueError) as error:
                result = {"execution_status": "failed", "comparison_verdict": "not-run", "reason": "artifact-inventory: " + str(error), "details": result["details"]}
            finish(db, attempt, result, manifest["limits"]["max_attempts"])
            reconcile(db, campaign_id)
            write_report(root, campaign_id)
        with transaction(db):
            remaining = db.execute("SELECT count(*) FROM jobs WHERE campaign_id=? AND state IN ('queued','running')", (campaign_id,)).fetchone()[0]
            if not remaining:
                db.execute("UPDATE campaigns SET state='completed' WHERE campaign_id=? AND state!='stopped'", (campaign_id,))
                event(db, campaign_id, "completed", {})
        reconcile(db, campaign_id)
        observation_tick(db, campaign_id)
        write_report(root, campaign_id)
        db.close()
    return snapshot(root, campaign_id)


def replay(root, repo, campaign_id, job_id, adapter=None):
    data = snapshot(root, campaign_id)
    jobs = [job for job in data["jobs"] if job["job_id"] == job_id]
    if not jobs:
        raise ValueError("unknown replay job")
    manifest = data["campaign"]["manifest"]
    manifest["campaign_id"] = campaign_id[:60] + "-replay-" + uuid.uuid4().hex[:12]
    manifest["jobs"] = [jobs[0]["spec"]]
    manifest["observation_seconds"] = 0
    manifest["provenance"] = {**manifest["provenance"], "replay_of": {"campaign_id": campaign_id, "job_id": job_id, "manifest_sha256": data["campaign"]["manifest_sha256"]}}
    return configure(root, repo, manifest, adapter)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("configure").add_argument("manifest", type=Path)
    for name in ("start", "status", "stop", "resume"):
        sub.add_parser(name).add_argument("campaign")
    replay_parser = sub.add_parser("replay")
    replay_parser.add_argument("campaign")
    replay_parser.add_argument("job")
    args = parser.parse_args(argv)
    if args.command == "init":
        connect(args.root).close()
        value = {"root": str(args.root.resolve()), "schema_version": 1}
    elif args.command == "configure":
        value = {"campaign_id": configure(args.root, args.repo, json.loads(args.manifest.read_text()))}
    elif args.command == "start":
        value = run_worker(args.root, args.repo, args.campaign)
    elif args.command == "status":
        value = snapshot(args.root, args.campaign)
    elif args.command == "replay":
        value = {"campaign_id": replay(args.root, args.repo, args.campaign, args.job)}
    else:
        control(args.root, args.campaign, args.command)
        value = snapshot(args.root, args.campaign)
    print(canonical(value))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError, sqlite3.Error) as error:
        print("local-lab: " + str(error), file=sys.stderr)
        sys.exit(2)
