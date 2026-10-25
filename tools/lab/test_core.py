"""Recovery, fencing and bounded-execution acceptance for the local queue."""
import contextlib
import json
import multiprocessing
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

import core


class FixtureAdapter:
    def validate(self, manifest, repo_root, config=None):
        return None

    def validate_job(self, manifest, job, repo_root, config=None):
        if job.get("parameters", {}).get("reject"):
            raise ValueError("unsupported fixture")

    def prepare(self, manifest, job, attempt_dir, repo_root, config=None):
        mode = job.get("parameters", {}).get("mode", "normal")
        progress = str(attempt_dir / "progress.json")
        code = """
import json,os,pathlib,subprocess,sys,time
mode,progress=sys.argv[1:]
pathlib.Path(progress+'.pid').write_text(str(os.getpid()))
if mode == 'output':
    os.write(1,b'x'*100000)
elif mode == 'nested':
    pathlib.Path(progress+'.stdout').write_bytes(b'x'*100000)
    time.sleep(1)
elif mode in ('stall','cancel','orphan'):
    if mode == 'orphan':
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
        pathlib.Path(progress+'.child').write_text(str(child.pid))
    time.sleep(60)
else:
    for sequence in range(3):
        pathlib.Path(progress).write_text(json.dumps({'sequence':sequence}))
        time.sleep(.03)
"""
        return {"argv": [sys.executable, "-c", code, mode, progress], "cwd": str(attempt_dir), "env": {}, "progress_file": progress}

    def result(self, manifest, job, attempt_dir, returncode):
        verdict = job.get("parameters", {}).get("verdict", "equal")
        return {"execution_status": "succeeded" if returncode == 0 else "failed", "comparison_verdict": verdict, "details": {}}


def child_worker(root, repo, cid, slot):
    core.run_worker(root, repo, cid, FixtureAdapter(), require_cgroup=False, heavy_lock=slot)


class CoreAcceptance(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.root = self.base / "state"
        self.repo = self.base / "repo"
        self.repo.mkdir()
        subprocess.run(["/usr/bin/git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["/usr/bin/git", "-C", str(self.repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture", "--allow-empty"], check=True)
        self.revision = subprocess.check_output(["/usr/bin/git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True).strip()
        self.adapter = FixtureAdapter()
        self.slot = self.base / "global.lock"

    def tearDown(self):
        self.temporary.cleanup()

    def manifest(self, jobs=None, **changes):
        value = {"schema_version": 1, "campaign_id": "fixture", "source_revision": self.revision, "pins": [],
                 "jobs": jobs or [{"job_id": "one", "template_id": "fixture", "parameters": {}}],
                 "limits": {**core.DEFAULT_LIMITS, "elapsed_seconds": 3, "stall_seconds": .5, "output_bytes": 4096, "min_free_bytes": 1},
                 "stop_conditions": {"max_failures": 100, "stop_on_divergence": False}, "provenance": {"fixture": True}}
        value.update(changes)
        own = Path(core.__file__).resolve()
        value["pins"] = [{"path": str(own), "sha256": core.digest(own)}] + value["pins"]
        return value

    def configure(self, manifest=None):
        return core.configure(self.root, self.repo, manifest or self.manifest(), self.adapter)

    def run_worker(self):
        return core.run_worker(self.root, self.repo, "fixture", self.adapter, require_cgroup=False, heavy_lock=self.slot)

    def test_manifest_identity_and_per_job_rejection_denominators(self):
        manifest = self.manifest(jobs=[{"job_id": "good", "template_id": "fixture", "parameters": {}},
                                       {"job_id": "bad", "template_id": "fixture", "parameters": {"reject": True}},
                                       {"job_id": "good", "template_id": "fixture", "parameters": {}}])
        self.configure(manifest)
        self.configure(manifest)
        data = core.snapshot(self.root, "fixture")
        self.assertEqual([job["state"] for job in data["jobs"]], ["queued", "rejected", "rejected"])
        manifest["provenance"]["changed"] = True
        with self.assertRaisesRegex(ValueError, "different manifest"):
            self.configure(manifest)
        data = self.run_worker()
        self.assertEqual(data["jobs"][0]["state"], "succeeded")
        self.assertEqual(len(data["attempts"]), 1)

    def test_source_and_pin_change_fail_closed(self):
        pin = self.repo / "input"
        pin.write_text("a")
        manifest = self.manifest(pins=[{"path": str(pin), "sha256": core.digest(pin)}])
        self.configure(manifest)
        pin.write_text("b")
        with self.assertRaisesRegex(ValueError, "changed pinned"):
            self.run_worker()
        manifest["source_revision"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "revision differs"):
            self.configure(manifest)
        self.assertEqual(len(core.snapshot(self.root, "fixture")["attempts"]), 0)

    def test_fencing_and_terminal_attempt_immutability(self):
        self.configure()
        db = core.connect(self.root)
        attempt = core.claim(db, self.root, "fixture")
        core.control(self.root, "fixture", "stop")
        core.control(self.root, "fixture", "resume")
        self.assertFalse(core.finish(db, attempt, {"execution_status": "succeeded", "comparison_verdict": "equal"}, 2))
        second = core.claim(db, self.root, "fixture")
        self.assertGreater(second["token"], attempt["token"])
        self.assertNotEqual(second["attempt_id"], attempt["attempt_id"])
        self.assertEqual(db.execute("SELECT state FROM jobs").fetchone()[0], "running")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("UPDATE attempts SET execution_status='succeeded' WHERE attempt_id=?", (attempt["attempt_id"],))
        self.assertEqual(db.execute("SELECT comparison_verdict FROM attempts WHERE attempt_id=?", (attempt["attempt_id"],)).fetchone()[0], "not-run")
        db.close()

    def test_recovery_preserves_attempt_and_retries_only_infrastructure(self):
        self.configure()
        db = core.connect(self.root)
        first = core.claim(db, self.root, "fixture")
        core.recover(db, "fixture", 2)
        second = core.claim(db, self.root, "fixture")
        self.assertEqual(second["ordinal"], 2)
        core.finish(db, second, {"execution_status": "infrastructure_failed", "comparison_verdict": "not-run", "reason": "fixture"}, 2)
        self.assertIsNone(core.claim(db, self.root, "fixture"))
        self.assertEqual(db.execute("SELECT state FROM jobs").fetchone()[0], "failed")
        self.assertEqual(db.execute("SELECT count(*) FROM attempts").fetchone()[0], 2)
        self.assertFalse(core.finish(db, first, {"execution_status": "succeeded", "comparison_verdict": "equal"}, 2))
        db.close()

    def test_publication_failure_is_durable_and_reconciled(self):
        self.configure()
        db = core.connect(self.root)
        attempt = core.claim(db, self.root, "fixture")
        core.finish(db, attempt, {"execution_status": "succeeded", "comparison_verdict": "equal", "details": {}}, 2)
        with mock.patch.object(core, "atomic_json", side_effect=OSError("disk fixture")):
            core.reconcile(db, "fixture")
        self.assertEqual(db.execute("SELECT publication_state FROM attempts").fetchone()[0], "pending")
        self.assertEqual(db.execute("SELECT state FROM jobs").fetchone()[0], "succeeded")
        core.reconcile(db, "fixture")
        self.assertEqual(db.execute("SELECT publication_state FROM attempts").fetchone()[0], "published")
        self.assertEqual(json.loads((Path(attempt["directory"]) / "result.json").read_text())["comparison_verdict"], "equal")
        db.close()

    def test_output_and_semantic_progress_limits_are_not_retried(self):
        self.configure(self.manifest(jobs=[{"job_id": mode, "template_id": "fixture", "parameters": {"mode": mode}} for mode in ("output", "nested", "stall")]))
        data = self.run_worker()
        self.assertEqual([attempt["reason"] for attempt in data["attempts"]], ["output-limit", "output-limit", "semantic-progress-stalled"])
        self.assertEqual(len(data["attempts"]), 3)
        self.assertLessEqual((Path(data["attempts"][0]["directory"]) / "stdout.log").stat().st_size, 4096)
        self.assertTrue(all(job["state"] == "failed" for job in data["jobs"]))

    def test_cancel_during_execution_fences_late_result(self):
        self.configure(self.manifest(jobs=[{"job_id": "one", "template_id": "fixture", "parameters": {"mode": "cancel"}}]))
        def cancel():
            deadline = time.monotonic()+5
            while time.monotonic() < deadline:
                if list((self.root / "attempts").glob("*/progress.json.pid")):
                    core.control(self.root, "fixture", "stop")
                    return
                time.sleep(.01)
            raise AssertionError("child did not start")
        thread = threading.Thread(target=cancel)
        thread.start()
        data = self.run_worker()
        thread.join()
        self.assertEqual(data["jobs"][0]["state"], "cancelled")
        self.assertEqual(data["attempts"][0]["comparison_verdict"], "not-run")
        self.assertEqual(data["attempts"][0]["reason"], "fenced-stale-publication")

    def test_single_global_slot_across_roots(self):
        self.configure()
        with core.lock(self.slot):
            with self.assertRaisesRegex(RuntimeError, "slot busy"):
                self.run_worker()
        self.assertEqual(len(core.snapshot(self.root, "fixture")["attempts"]), 0)

    def test_worker_sigkill_and_orphan_slot_then_recovery(self):
        self.configure(self.manifest(jobs=[{"job_id": "one", "template_id": "fixture", "parameters": {"mode": "orphan"}}]))
        worker = multiprocessing.Process(target=child_worker, args=(self.root, self.repo, "fixture", self.slot))
        worker.start()
        deadline = time.monotonic()+5
        paths = []
        while time.monotonic() < deadline:
            paths = list((self.root / "attempts").glob("*/progress.json.child"))
            if paths:
                break
            time.sleep(.01)
        self.assertTrue(paths)
        child_pid = int(paths[0].with_suffix(".pid").read_text())
        escaped_pid = int(paths[0].read_text())
        os.kill(worker.pid, signal.SIGKILL)
        worker.join(3)
        try:
            with self.assertRaisesRegex(RuntimeError, "slot busy"):
                with core.lock(self.slot):
                    pass
        finally:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child_pid, signal.SIGKILL)
            with contextlib.suppress(ProcessLookupError):
                os.kill(escaped_pid, signal.SIGKILL)
        deadline = time.monotonic()+3
        while time.monotonic() < deadline:
            try:
                with core.lock(self.slot):
                    break
            except RuntimeError:
                time.sleep(.01)
        db = core.connect(self.root)
        core.recover(db, "fixture", 2)
        data = core.snapshot(self.root, "fixture")
        self.assertEqual(data["attempts"][0]["reason"], "worker-interrupted")
        self.assertEqual(data["jobs"][0]["state"], "queued")
        db.close()

    def test_comparison_divergence_stops_without_execution_failure(self):
        self.configure(self.manifest(jobs=[{"job_id": "one", "template_id": "fixture", "parameters": {"verdict": "different"}}, {"job_id": "two", "template_id": "fixture", "parameters": {}}], stop_conditions={"max_failures": 100, "stop_on_divergence": True}))
        data = self.run_worker()
        self.assertEqual(data["campaign"]["state"], "stopped")
        self.assertEqual(data["jobs"][0]["execution_status"], "succeeded")
        self.assertEqual(data["jobs"][0]["comparison_verdict"], "different")
        self.assertEqual(data["jobs"][1]["state"], "queued")

    def test_idle_horizon_accounts_real_time_without_repeating_jobs(self):
        self.configure(self.manifest(observation_seconds=1.5))
        before = time.monotonic()
        data = self.run_worker()
        self.assertGreaterEqual(time.monotonic()-before, 1.5)
        self.assertGreater(data["campaign"]["idle_seconds"], .1)
        self.assertEqual(len(data["attempts"]), 1)
        self.assertEqual(data["campaign"]["state"], "completed")

    def test_published_tampering_is_visible_and_never_overwritten(self):
        self.configure()
        data = self.run_worker()
        path = Path(data["attempts"][0]["directory"]) / "stdout.log"
        path.write_text("tampered")
        db = core.connect(self.root)
        core.reconcile(db, "fixture", verify_published=True)
        data = core.snapshot(self.root, "fixture")
        self.assertEqual(data["attempts"][0]["publication_state"], "corrupt")
        self.assertEqual(data["campaign"]["stop_reason"], "artifact-integrity")
        self.assertEqual(path.read_text(), "tampered")
        db.close()

    def test_cancel_kills_descendants_that_escape_process_group(self):
        self.configure(self.manifest(jobs=[{"job_id": "one", "template_id": "fixture", "parameters": {"mode": "orphan"}}]))
        child = []
        def cancel():
            deadline = time.monotonic()+5
            while time.monotonic() < deadline:
                paths = list((self.root / "attempts").glob("*/progress.json.child"))
                if paths:
                    child.append(int(paths[0].read_text()))
                    core.control(self.root, "fixture", "stop")
                    return
                time.sleep(.01)
        thread = threading.Thread(target=cancel)
        thread.start()
        self.run_worker()
        thread.join()
        self.assertTrue(child)
        with self.assertRaises(ProcessLookupError):
            os.kill(child[0], 0)

    def test_boot_change_cannot_falsely_complete_observation(self):
        self.configure()
        self.run_worker()
        db = core.connect(self.root)
        db.execute("UPDATE campaigns SET observation_boot_id='different-boot',state='running'")
        with self.assertRaisesRegex(RuntimeError, "boot changed"):
            core.observation_tick(db, "fixture")
        db.close()

    def test_elapsed_disk_and_free_space_failures_are_terminal(self):
        cases = (("elapsed-limit", {"elapsed_seconds": .1, "stall_seconds": 2}),
                 ("disk-limit", {"disk_bytes": 64}),
                 ("disk-free-floor", {"min_free_bytes": 10**18}))
        for index, (expected, changes) in enumerate(cases):
            with self.subTest(reason=expected):
                manifest = self.manifest(campaign_id="limit-"+str(index), jobs=[{"job_id": "one", "template_id": "fixture", "parameters": {"mode": "stall"}}])
                manifest["limits"].update(changes)
                self.configure(manifest)
                data = core.run_worker(self.root, self.repo, manifest["campaign_id"], self.adapter, require_cgroup=False, heavy_lock=self.slot)
                self.assertEqual(data["attempts"][0]["reason"], expected)
                self.assertEqual(len(data["attempts"]), 1)
                self.assertEqual(data["jobs"][0]["state"], "failed")

    def test_report_failure_does_not_retry_success(self):
        self.configure()
        import report
        with mock.patch.object(report, "write_report", side_effect=AttributeError("fixture presentation shape")):
            data = self.run_worker()
        self.assertEqual(data["jobs"][0]["state"], "succeeded")
        self.assertEqual(len(data["attempts"]), 1)
        self.assertTrue(any(event["kind"] == "report-publication-failed" for event in data["events"]))

    def test_global_slot_cgroup_fence_covers_nested_closed_descriptors(self):
        with core.lock(self.slot) as fd:
            with mock.patch.object(core, "cgroup_populated", return_value=False):
                core.register_slot_owner(fd, {"path": "/old.service"})
            with mock.patch.object(core, "cgroup_populated", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "still populated"):
                    core.register_slot_owner(fd, {"path": "/new.service"})
            with mock.patch.object(core, "cgroup_populated", return_value=False):
                core.register_slot_owner(fd, {"path": "/new.service"})

    def test_initial_rejections_apply_failure_stop_condition_before_work(self):
        manifest = self.manifest(jobs=[{"job_id": "bad", "parameters": {"reject": True}}], stop_conditions={"max_failures": 1, "stop_on_divergence": False})
        self.configure(manifest)
        data = self.run_worker()
        self.assertEqual(data["campaign"]["stop_reason"], "stop-condition")
        self.assertEqual(data["campaign"]["state"], "stopped")
        self.assertEqual(len(data["attempts"]), 0)

    def test_unobserved_gap_censors_horizon_and_fences_active_job(self):
        self.configure(self.manifest(observation_seconds=86400))
        db = core.connect(self.root)
        now = time.monotonic()
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        db.execute("UPDATE campaigns SET observation_boot_id=?,observation_start_monotonic=?,observation_last_tick=?", (boot, now-100, now-40))
        attempt = core.claim(db, self.root, "fixture")
        core.observation_tick(db, "fixture")
        data = core.snapshot(self.root, "fixture")
        self.assertEqual(data["campaign"]["stop_reason"], "observation-gap")
        self.assertEqual(data["campaign"]["observation_qualified"], 0)
        self.assertEqual(data["campaign"]["idle_seconds"], 0)
        self.assertEqual(data["jobs"][0]["state"], "cancelled")
        self.assertFalse(core.finish(db, attempt, {"execution_status": "succeeded", "comparison_verdict": "equal"}, 2))
        db.close()

    def test_completed_observation_keeps_elapsed_frozen_during_reconciliation(self):
        self.configure(self.manifest(observation_seconds=86400))
        db = core.connect(self.root)
        db.execute("UPDATE campaigns SET state='completed',observation_boot_id='historic',observation_elapsed_seconds=86400,observation_last_tick=0")
        self.assertEqual(core.observation_tick(db, "fixture"), 86400)
        self.assertEqual(core.snapshot(self.root, "fixture")["campaign"]["observation_qualified"], 1)
        db.close()

    def test_finite_limits_and_cgroup_enforcement(self):
        manifest = self.manifest()
        manifest["limits"]["elapsed_seconds"] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite"):
            self.configure(manifest)
        self.configure()
        with mock.patch.object(core, "check_cgroup", side_effect=RuntimeError("missing cgroup")):
            with self.assertRaisesRegex(RuntimeError, "missing cgroup"):
                core.run_worker(self.root, self.repo, "fixture", self.adapter)


if __name__ == "__main__":
    unittest.main()
