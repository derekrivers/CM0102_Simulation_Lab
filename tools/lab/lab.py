#!/usr/bin/env python3
"""Operator entry point for the approved single-worker WSL lab."""
import argparse
import datetime
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
UNIT = "cm0102-local-lab.service"
DEFAULT_ROOT = Path.home() / ".local/share/cm0102-lab"


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".publish-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def core_command(root, *args, capture=False):
    result = subprocess.run(
        [sys.executable, str(REPO / "tools/lab/core.py"), "--root", str(root),
         "--repo", str(REPO), *map(str, args)],
        text=True, capture_output=capture, check=True)
    return result.stdout if capture else None


def selected(root, supplied):
    if supplied:
        return supplied
    path = root / "operator.json"
    if not path.exists():
        raise ValueError("No campaign selected. Start one with: lab.py start synthetic")
    return json.loads(path.read_text())["campaign_id"]


def service_active():
    return subprocess.run(["systemctl", "--user", "is-active", "--quiet", UNIT],
                          check=False).returncode == 0


def worker_command_matches(command, root, campaign):
    expected = [str(REPO / "tools/lab/core.py").encode(), b"--root", str(root).encode(),
                b"--repo", str(REPO).encode(), b"start", campaign.encode(), b""]
    return (len(command) == len(expected) + 1
            and Path(os.fsdecode(command[0])).resolve() == Path(sys.executable).resolve()
            and command[1:] == expected)


def launch(root, campaign):
    if service_active():
        raise ValueError("A local lab worker is already active. Use status or stop first.")
    if not (Path("/run/user") / str(os.getuid())).is_dir():
        raise ValueError("WSL user systemd is unavailable. Follow docs/runbooks/local-lab.md setup.")
    subprocess.run(["systemctl", "--user", "reset-failed", UNIT],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    command = [
        "systemd-run", "--user", "--unit=" + UNIT, "--collect",
        "--description=CM0102 approved local research campaign",
        "--property=CPUQuota=100%", "--property=MemoryMax=2147483648",
        "--property=MemorySwapMax=0", "--property=TasksMax=128",
        "--property=KillMode=control-group", "--property=SendSIGKILL=yes",
        "--property=TimeoutStopSec=15", "--property=Restart=on-failure",
        "--property=RestartPreventExitStatus=2",
        "--property=RestartSec=3", "--property=StartLimitIntervalSec=60",
        "--property=StartLimitBurst=3", "--property=UMask=0077",
        "--property=WorkingDirectory=" + str(REPO),
        sys.executable, str(REPO / "tools/lab/core.py"), "--root", str(root),
        "--repo", str(REPO), "start", campaign]
    subprocess.run(command, check=True)
    atomic_json(root / "operator.json", {"campaign_id": campaign, "repo": str(REPO)})
    print(f"Campaign {campaign} launched as {UNIT}.")
    print("The WSL worker continues after this shell and the agent/chat close.")
    print(f"Report: {root / 'campaigns' / campaign / 'report.html'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup", help="One-time private input configuration")
    setup.add_argument("--config", type=Path, required=True)
    start = sub.add_parser("start", help="Start an approved built-in profile")
    start.add_argument("profile", choices=["synthetic", "regression", "research-squad"])
    start.add_argument("--campaign")
    start.add_argument("--qualification-hours", type=float, default=0)
    for verb in ("status", "stop", "resume", "report", "restart"):
        child = sub.add_parser(verb)
        child.add_argument("campaign", nargs="?")
    replay = sub.add_parser("replay")
    replay.add_argument("job")
    replay.add_argument("--campaign")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    os.umask(0o077)
    if args.command == "setup":
        config = json.loads(args.config.read_text())
        if not isinstance(config, dict):
            raise ValueError("Private configuration must be a JSON object.")
        core_command(root, "init", capture=True)
        atomic_json(root / "config.json", config)
        print(f"Private configuration saved: {root / 'config.json'}")
        return
    if args.command == "start":
        if service_active():
            raise ValueError("A worker is already active; use status or stop first.")
        if not 0 <= args.qualification_hours <= 24:
            raise ValueError("Qualification hours must be between 0 and 24.")
        from workloads import build_profile
        config_path = root / "config.json"
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
        campaign = args.campaign or (args.profile + "-" + datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        manifest = build_profile(args.profile, config, REPO, campaign)
        if args.qualification_hours:
            manifest["observation_seconds"] = int(args.qualification_hours * 3600)
        core_command(root, "init", capture=True)
        path = root / "pending-manifest.json"
        atomic_json(path, manifest)
        core_command(root, "configure", path, capture=True)
        launch(root, campaign)
        return
    campaign = selected(root, args.campaign)
    if args.command == "status":
        snapshot = json.loads(core_command(root, "status", campaign, capture=True))
        state = snapshot["campaign"]
        print(f"Campaign {campaign}: {state['state']}; worker {'active' if service_active() else 'inactive'}")
        for job in snapshot["jobs"]:
            print(f"  {job['job_id']}: {job['state']}; comparison={job['comparison_verdict']}; attempts={job['attempts']}"
                  + (f"; {job['reason']}" if job.get("reason") else ""))
        print(f"Recorded execution {state.get('active_seconds', 0):.3f}s; idle queue {state.get('idle_seconds', 0):.3f}s")
        print(f"Report: {root / 'campaigns' / campaign / 'report.html'}")
    elif args.command == "report":
        from core import snapshot
        from report import write_report
        print(write_report(root, campaign, snapshot(root, campaign)))
    elif args.command == "stop":
        core_command(root, "stop", campaign, capture=True)
        print("Stop recorded. The worker retains partial evidence and pauses queued work.")
    elif args.command == "resume":
        if service_active():
            raise ValueError("Worker is still active; wait for stop to finish before resume.")
        data = json.loads(core_command(root, "status", campaign, capture=True))
        state = data["campaign"]["state"]
        if state == "stopped":
            core_command(root, "resume", campaign, capture=True)
        elif state == "completed" and any(attempt["publication_state"] == "pending" for attempt in data["attempts"]):
            pass  # Reconcile retained results without requeueing successful jobs.
        elif state not in {"ready", "running"}:
            raise ValueError("Campaign is terminal. Replay a selected job or start a new campaign.")
        launch(root, campaign)
    elif args.command == "replay":
        if service_active():
            raise ValueError("Worker is active; wait for completion or stop before replay.")
        replay = json.loads(core_command(root, "replay", campaign, args.job, capture=True))
        launch(root, replay["campaign_id"])
    elif args.command == "restart":
        if not service_active():
            raise ValueError("No worker is active. Use resume to recover a stopped campaign.")
        from core import snapshot, connect, transaction, event
        data = snapshot(root, campaign)
        workers = [item for item in data["events"] if item["kind"] == "worker-started"]
        current = subprocess.check_output(["systemctl", "--user", "show", "--property=MainPID", "--value", UNIT], text=True).strip()
        if not workers or current != str(workers[-1]["detail"].get("pid")):
            raise ValueError("The active worker belongs to another campaign. No process was signalled.")
        pid = int(current)
        descriptor = os.pidfd_open(pid)
        try:
            command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            if not worker_command_matches(command, root, campaign):
                raise ValueError("Worker command identity differs. No process was signalled.")
            db = connect(root)
            with transaction(db):
                event(db, campaign, "restart-requested", {"pid": pid, "source": "operator-or-frozen-drill"})
            db.close()
            signal.pidfd_send_signal(descriptor, signal.SIGKILL)
        finally:
            os.close(descriptor)
        print("Injected worker termination; systemd will clean descendants and restart it.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Local lab: {error}", file=sys.stderr)
        sys.exit(2)
