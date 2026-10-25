# Local unattended research lab

This is the bounded local milestone, using one WSL worker and a private SQLite
store. Full P01/P03 gates remain open. The worker executes approved templates;
it cannot change source, rewrite reference results or admit hypotheses.

## Setup once

Use Ubuntu WSL with systemd, Python 3.12 and the pinned Rust toolchain. Build on
the WSL native filesystem, outside OneDrive. Existing private original files,
captures and qualified Bosman deployment remain outside Git.

```sh
cd /home/derek/cm0102-lab
cargo build --locked --workspace --all-targets -j 1
cargo build --locked -p cm-rng --example corpus --target wasm32-unknown-unknown -j 1
loginctl enable-linger "$USER"
```

The delivered checkout is `/home/derek/cm0102-lab`; default private state is
`/home/derek/.local/share/cm0102-lab`. For another user/location, use
`lab.py --root /absolute/private/state` and Windows Setup parameters below.
Keep the worker's source checkout at its accepted revision. Editing pinned
source, inputs or tools makes an existing campaign reject rather than silently
changing the replay. Preserve its old checkout/configuration when upgrading.

Create a private JSON configuration once. Each value is an absolute WSL path:

```json
{
  "python": "/usr/bin/python3",
  "node": "/usr/bin/node",
  "rng_native": "/home/derek/cm0102-lab/target/debug/examples/corpus",
  "rng_wasm": "/home/derek/cm0102-lab/target/wasm32-unknown-unknown/debug/examples/corpus.wasm",
  "oracle_python": "/private/oracle-venv/bin/python",
  "original_executable": "/private/original/cm0102.exe",
  "retained_capture": "/private/retained/snapshot",
  "bosman_supervisor": "/home/derek/cm0102-lab/target/debug/lab-cli",
  "bosman_adapter": "/home/derek/cm0102-lab/target/debug/lab-bosman-adapter",
  "bosman_config": "/private/bosman-adapter-config.json",
  "bosman_request": "/private/qualified-bosman-request.json"
}
```

The oracle interpreter needs the already-qualified Unicorn 2.1.4 and Capstone
5.0.7. Keep its virtual-environment invocation path. The retained capture is the
previously qualified `image.bin`/`heap.bin` pair, verified by hashes. The Bosman
request/config uses the existing qualified seed-1, fixed-clock, classic,
14-day `normal,again` profile. Configuration is a locator, not permission to
widen a profile. The adapters pin tools and all declared inputs and validate
the complete clean-file tree through the existing Rust adapter.

```sh
python3 tools/lab/lab.py setup --config /private/my-lab-inputs.json
```

From Windows, open `\\wsl.localhost\Ubuntu\home\derek\cm0102-lab\tools\lab`
in Explorer. Run this once from PowerShell (the JSON remains in WSL):

```powershell
.\Lab.cmd Setup -Distro Ubuntu -WslUser derek -Repo /home/derek/cm0102-lab -StateRoot /home/derek/.local/share/cm0102-lab
```

Optional `-ConfigFile /private/my-lab-inputs.json` performs the Python setup too.
Windows launcher settings are in `%LOCALAPPDATA%\CM0102Lab\launcher.json`;
Setup also installs `Lab.cmd` and `Lab.ps1` there for a Windows-native entry point.
private input configuration is in the WSL state directory's `config.json`.
No original executable, save, raw memory or private configuration belongs in Git.

## Start, inspect and review

Double-click `Lab.cmd` for the menu, or use these commands from a fresh Windows
shell in that directory. No per-run manifest editing is necessary.

```powershell
.\Lab.cmd Start synthetic
.\Lab.cmd Status
.\Lab.cmd Report
.\Lab.cmd Start regression
.\Lab.cmd Start research-squad
```

Wait for the current worker to finish before starting another. Every start
freezes a new campaign identity, source revision, input/tool digests, resource
limits and stop conditions. `synthetic` tests the execution path. `regression`
runs the qualified RNG native/WASM corpus, original R10 instruction/control
corpus and fixed Bosman endpoint. `research-squad` is a read-only structural
question under its separately frozen research protocol; observations never
become an admitted squad or game rule automatically.

`elapsed_seconds` bounds each physical attempt. A finite campaign's useful-work
upper bound is jobs × maximum attempts × that elapsed bound, plus bounded
collection. `observation_seconds` is a minimum service observation horizon,
including explicit idle time; it never interrupts a useful job merely because
24 hours elapsed. Stop conditions can end the campaign earlier and leave a
visible unfulfilled qualification target.

The persistent worker is `cm0102-local-lab.service` in the WSL user systemd
manager. It has one CPU quota, 2 GiB memory, zero swap and 128 tasks. The queue
and global host slot prevent conflicting lab workers, including across private
state roots. One heavy build/simulation at a time remains an operator rule for
other development tools; build before starting a campaign.
Transient systemd unit accounting is collected after exit; durable per-attempt
cgroup resource samples remain in the database and report. Deterministic startup
errors (exit 2) prevent automatic restart; unexpected worker failure has a bounded
systemd restart rate and separately bounded job retry budget.

Closing this shell or the agent/chat leaves the service running. Keep the PC
awake and WSL running during qualification. PC suspend/shutdown or `wsl --shutdown`
interrupts the run; recovery retains interrupted attempts but cannot count
unobserved time as successful continuous operation.

Use the Windows entry point for unattended launches. It starts a hidden Windows
holder with an acknowledged token and a foreground WSL client for the campaign's
finite lifetime. This is necessary because [systemd services do not themselves
keep WSL alive](https://learn.microsoft.com/en-us/windows/wsl/systemd/). The holder
requests system availability without changing saved power policy or keeping the
display on, and exits when the campaign stops or completes. The worker still
executes every job under systemd. Direct WSL-only CLI launches require retaining
a WSL foreground client and are diagnostic/manual operation, not the Windows
unattended launch path. User logoff, explicit sleep/shutdown and WSL shutdown
remain interruptions; this is a local-PC service, not a machine-reboot service.

`Report` opens `STATE/campaigns/CAMPAIGN/report.html` in your browser. The matching
`report.json` and frozen `manifest.json` provide machine-readable accounting.
Each physical attempt lives in `STATE/attempts/ATTEMPT_ID`; the report links
retained requests, results and stream prefixes. Reports refresh automatically
during execution and at completion; no agent is needed to interpret endpoints.
These reports are private local output.

## Stop, resume, recovery and replay

```powershell
.\Lab.cmd Stop
.\Lab.cmd Status
.\Lab.cmd Resume
.\Lab.cmd Replay 001-rng-native-wasm-v1
```

Stop records cancellation, fences active publication, cleans up descendants
and retains partial evidence. Wait until the service exits before Resume.
Resume requeues operator-cancelled jobs in the same campaign; completed results
are preserved. Replay creates a separate campaign for the selected logical job
and retains the original. Changed source/tool/input identities reject replay;
use the original accepted checkout and private inputs.

An unexpected worker death triggers bounded systemd restart and durable queue
recovery. An explicit recovery drill is `Lab.cmd Restart`: it kills the worker
main process, after which systemd cleans its descendants before replacement.
Infrastructure retries are bounded by the frozen manifest. Deterministic
mismatches retain `different` and are not endlessly retried.

Resume also reconciles pending publication in an otherwise completed campaign,
without requeueing its successful jobs. Corrupt published evidence is an explicit
integrity stop and is never repaired by silently replacing accepted artifacts.

If WSL was shut down, open Ubuntu, verify the accepted checkout and invoke
Resume for an operator-stopped campaign. For an interrupted campaign still
marked running, use the recovery launch described by `lab.py resume`; do not
delete its database, attempt directory or manifest to force a rerun.

For diagnostics:

```sh
systemctl --user status cm0102-local-lab.service
journalctl --user -u cm0102-local-lab.service --no-pager -n 80
python3 tools/lab/lab.py status
```

A busy execution slot means an existing worker/descendant still owns it. Do not
remove the lock file to force concurrency. Missing or changed pins require
restoring the recorded files or starting a newly frozen campaign. Output, disk,
elapsed and semantic-progress exhaustion retain an explicit failed outcome.
Insufficient free storage may prevent publication; the database remains the
authority and reconciliation retries incomplete result publication on recovery.

## Qualification

After the reviewed short pilot and frozen qualification protocol, the operator
entry point supports `Lab.cmd Start regression -Qualification`, requesting an
actual 24-hour observation horizon. Useful finite work runs once; remaining
time is explicit idle/queue accounting. A short run never establishes the
24-hour milestone. See the progress record for the actual delivered revision,
pilot duration, failure drills, replay evidence and current qualification state.
