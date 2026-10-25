#!/usr/bin/env python3
"""Keep a foreground WSL client attached to the bounded Windows-launched campaign."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import os
import fcntl
import core


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    root, cid = args.root.resolve(), args.campaign
    os.umask(0o077)
    host = root / "host"
    host.mkdir(parents=True, exist_ok=True, mode=0o700)
    owner = (host / (cid + ".lock")).open("a+")
    owner_deadline = time.monotonic() + 15
    while True:
        try:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() > owner_deadline:
                raise RuntimeError("A lifetime holder already owns this campaign; wait for stop to complete.")
            time.sleep(.2)
    data = core.snapshot(root, cid)
    stop_sequence = max((event["sequence"] for event in data["events"] if event["kind"] == "stop"), default=0)
    manifest = data["campaign"]["manifest"]
    maximum = (len(manifest["jobs"]) * manifest["limits"]["max_attempts"]
               * manifest["limits"]["elapsed_seconds"]
               + manifest.get("observation_seconds", 0) + 180)
    deadline = time.monotonic() + maximum
    record = {"campaign_id": cid, "token": args.token, "pid": os.getpid(), "started": time.time(),
              "purpose": "foreground WSL lifetime holder; systemd executes approved jobs"}
    destination = root / "host" / (cid + ".json")
    missing_since = None
    while True:
        data = core.snapshot(root, cid)
        state = data["campaign"]["state"]
        stopped_since = any(event["kind"] == "stop" and event["sequence"] > stop_sequence for event in data["events"])
        active = subprocess.run(["/usr/bin/systemctl", "--user", "is-active", "--quiet",
                                 "cm0102-local-lab.service"], check=False).returncode == 0
        record.update(heartbeat=time.time(), state=state, worker_active=active)
        if not active:
            missing_since = missing_since or time.monotonic()
        else:
            missing_since = None
        selected = json.loads((root / "operator.json").read_text())["campaign_id"]
        owns_service = True
        if state in {"completed", "stopped"}:
            workers = [event for event in data["events"] if event["kind"] == "worker-started"]
            current = subprocess.run(["/usr/bin/systemctl", "--user", "show", "--property=MainPID",
                                      "--value", "cm0102-local-lab.service"], text=True, capture_output=True, check=False)
            owns_service = bool(workers) and current.stdout.strip() == str(workers[-1]["detail"].get("pid"))
        if ((state in {"completed", "stopped"} and (not active or selected != cid or not owns_service))
                or (stopped_since and state not in {"stopped"})):
            record.update(finished=time.time(), outcome="worker-terminal")
            core.atomic_json(destination, record)
            return 0
        reason = None
        if missing_since and time.monotonic() - missing_since > 30:
            reason = "host-worker-unavailable"
        elif time.monotonic() > deadline:
            reason = "host-holder-deadline"
        if reason:
            core.control(root, cid, "stop")
            db = core.connect(root)
            with core.transaction(db):
                db.execute("UPDATE campaigns SET stop_reason=?,observation_qualified=0 WHERE campaign_id=?", (reason,cid))
                core.event(db,cid,reason,{"holder":record})
            db.close()
            core.write_report(root,cid)
            record.update(finished=time.time(), outcome=reason)
            core.atomic_json(destination, record)
            return 2
        core.atomic_json(destination, record)
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
