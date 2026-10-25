# Local lab v1: bounded single-PC unattended research

Status: implementation contract for the 25 October 2026 programme redirection.
This milestone uses one Linux worker and SQLite on the PC's WSL-native filesystem.
It is deliberately narrower than the retained PostgreSQL/distributed P01 design
and continuous scientific P03 scope. It cannot close either whole phase gate.
A 24-hour observation is evidence only after actual elapsed execution; launching
it, successful fixture tests or correctly classified failures cannot establish
that gate. No job promotes hypotheses, rewrites reference data or modifies Git.

## Frozen campaign and adapters

`tools/lab/core.py` owns queueing, attempt identity, resource/watchdog controls,
publication and recovery. `workloads.py` owns the fixed approved workload
allowlist, template parameters, source/input/tool identities and endpoint
interpretation. Its interface is:

- `validate(manifest, repo_root, config=None)` validates shared template policy.
- `validate_job(manifest, job, repo_root, config=None)` admits one logical job.
- `prepare(manifest, job, attempt_dir, repo_root, config=None)` returns fixed
  `argv`, `cwd`, sanitized `env`, and optional `progress_file`.
- `result(manifest, job, attempt_dir, returncode)` returns `execution_status`,
  `comparison_verdict` and structured `details`.

Execution statuses are `succeeded`, `failed`, `infrastructure_failed`,
`cancelled`, `rejected`; comparison is independently `not-run`, `equal`,
`different`, `inconclusive`, `not-comparable`. A successful process with
`different` is a divergence, never an execution failure disguised as equality.
The real Bosman route reuses the existing Rust `lab-cli execute-process`
supervisor; Python remains research orchestration, never game rules.

A schema-1 manifest contains `campaign_id`, the exact 40-character Git
`source_revision`, global `pins` (`path`, lowercase `sha256`), finite `jobs`
(`job_id`, approved `template_id`, `parameters`, optional additional `pins`),
`limits`, `stop_conditions`, and `provenance`. Configuration comes from the
private state directory's `config.json`; the workload registry binds its digest
and all referenced script/binary/input digests. No shell, arbitrary executable
or unreviewed generated worker is admitted from a manifest. Canonical UTF-8 JSON
uses sorted keys, compact separators and rejects nonfinite numbers. Campaign
identity permanently binds those bytes and their SHA-256. A replay creates a
new campaign referring to the old manifest/job and has no inherited observation
horizon.

Every per-attempt limit is explicit: `max_jobs`, `elapsed_seconds`, `stall_seconds`,
`output_bytes`, `disk_bytes`, `min_free_bytes`, `max_attempts`. All must be finite
and positive; attempts are capped at three and logical jobs at 10,000. Stop
conditions are positive `max_failures` and boolean `stop_on_divergence`.
`observation_seconds` optionally requests up to 86,400 actual seconds. `elapsed_seconds` is a maximum per physical attempt; finite job and retry counts
bound total useful work by their product. `observation_seconds` is a minimum
observation horizon, checked between attempts, not a job deadline. A finite
work list that finishes early enters explicitly accounted idle observation;
it does not repeat regression work to manufacture activity.

Global invalid source/policy rejects admission. Malformed/unsupported per-job
inputs create stable rejected denominator records while valid jobs remain
queued. Source and input/tool hashes are checked at configure, worker start and
before each physical attempt. The adapter also validates private configuration.

## Durable state and ownership

SQLite uses WAL, `synchronous=FULL`, foreign keys and short `BEGIN IMMEDIATE`
transactions. Logical jobs move queued → running → terminal; infrastructure
interruption alone can return a job to queued within its attempt budget. Each
claim increments a fencing token and creates a fresh UUID directory and physical
attempt. Attempts are never reused. SQLite triggers forbid identity changes and
terminal result changes. A conditional token/state update accepts one current
result; stale output is retained as fenced cancellation without updating the
current job. Operator stop increments tokens before terminating work, and resume
requeues only operator-cancelled jobs. Divergence/failure stop conditions preserve
remaining queued jobs visibly.

A per-root worker flock and fixed per-user
`/run/user/UID/cm0102-lab-heavy.lock` serialize workers across state roots. The
child inherits the heavy-lock descriptor. Atomically persisted slot-owner metadata
also refuses a different service while its predecessor cgroup is still
populated, covering nested children that close inherited descriptors. Worker death cannot release the slot
while its still-running inherited child holds it. The production launcher uses a
single stable user service; systemd kills all service descendants before restart.
Only then can the next worker acquire the global slot, classify interrupted
attempts, reconcile publication and claim a new fenced attempt. This mechanism is
one-host ownership, not a distributed lease implementation.

The state directory and all raw/private outputs stay outside Git. The database
is authoritative. Final results and artifact inventories commit to SQLite before
atomic/fsynced `result.json` publication. Publication failure leaves a pending
record and a durable event for reconciliation; no successful attempt is retried
because a report or result file could not publish. Inventories bind relative
paths, sizes and SHA-256 after child termination and stream flush. Symlinks are
not accepted as artifacts. Published result/inventory tampering is visible and
stops the campaign; recovery never silently replaces a changed published file.
A missing canonical campaign file can be regenerated from the database; a changed
one rejects startup.

## Resource isolation, controls and crash boundary

Measured PC capacity supplied to this increment: 16 logical CPUs, 12 GiB RAM and
approximately 930 GiB free. The Windows launcher starts a hidden, finite campaign lifetime holder in a
separate process. Its foreground `wsl.exe` client remains attached while Linux
`hold.py` observes the service/database. Systemd services alone do not keep WSL
alive. A fresh handshake proves the holder is attached before the launcher
reports unattended readiness. The holder can stop/censor an unavailable worker;
it never claims jobs. Its temporary Windows system-awake request ends with the
campaign and changes no persistent power policy. Explicit Windows logout,
shutdown or forced WSL shutdown remains an interruption, not qualification.

The trusted launcher places the entire worker tree
in a cgroup-v2 systemd user service with `CPUQuota=100%`, `MemoryMax=2G`,
`MemorySwapMax=0`, `TasksMax=128`, `KillMode=control-group`, `SendSIGKILL=yes`,
`Restart=on-failure` and a bounded restart delay. Core verifies that its service
cgroup has finite CPU, memory and PID quotas before unattended work. The launcher
owns the service lifecycle properties; direct test-only `require_cgroup=False`
is a Python fixture API and is never a production CLI flag.

Streams are drained independently through a shared byte budget, and retained
outer pipe prefixes never exceed that budget. Nested `*.stdout`, `*.stderr`,
`*.log` and `stdout.ndjson` stream files are included in the monitored aggregate
output budget. Those direct-file streams and disk growth have sampled overshoot;
they are not presented as hard filesystem quotas. The outer watchdog checks elapsed monotonic
time, output volume, attempt-tree bytes and a filesystem free-space floor.
Adapters publish bounded JSON progress frames containing an increasing integer
`sequence`; repeated timestamps/identical frames and mere stdout activity cannot
reset semantic progress. Heartbeat frame parsing is capped at 64 KiB. Resource
failures and stalled progress are terminal failures, never infrastructure retries.
Disk enforcement is a monitored bound with sampling overshoot, not a filesystem
quota. Private input pinning occurs before launch; adapters must not copy an
unbounded input in their small preparation phase.

The Linux worker is a child subreaper. Cancellation/deadline cleanup discovers
all descendants (including a child that starts a new session), uses PID file
descriptors for race-safe signals, kills process groups and reaps adopted
children. This complements the Rust supervisor's own bounded process controls.
On worker SIGKILL/OOM, the enclosing systemd service's whole-cgroup cleanup is the
crash boundary. Unit lifecycle and escaped-descendant failure drills are required
alongside the Python tests before unattended qualification.

Per-attempt results contain before/after cgroup CPU counters, current/peak memory,
OOM events and process counts where available. `memory.peak` is service lifetime
peak, not falsely attributed as an isolated attempt peak. Observation persists a
Linux boot ID, monotonic start, wall-clock start, monotonic elapsed, and separate
active/idle execution accounts. Wall-clock jumps cannot complete the horizon. A
changed boot ID rejects continuation of that observation and requires a new
campaign; interrupted state remains available. Restart downtime is visible as
the difference between total horizon age and recorded active/idle time. A gap
over thirty seconds between service observations conservatively stops and
censors a nonzero qualification horizon, fencing active work; the gap is never
added to healthy active/idle accounts. This includes long VM pauses or restart
outages. The report must show `observation_qualified=0` and the explicit gap
event rather than present that horizon as qualified.

## Public commands and acceptance

The operator-facing launcher owns `init`, `configure`, `start`, `status`, `stop`,
`resume`, `report`, `replay`. The internal foreground CLI is
`python3 tools/lab/core.py --root STATE --repo REPO COMMAND ...` with configure
accepting a manifest path; start/status/stop/resume accepting campaign ID; replay
accepting campaign ID plus logical job ID. Its success code is 0 and anticipated
validation/resource/startup error code is 2. `snapshot(root, campaign_id)` returns
JSON-serializable `campaign`, `jobs`, `attempts`, `events`. The report is updated
after terminal attempts, periodically during idle observation and at completion.

`python3 -m unittest discover -s tools/lab -p test_core.py -v` covers canonical
identity, mixed rejected/good records, changed inputs/revisions, immutable
attempts, fenced publication after cancel/resume, bounded infrastructure retries,
publication failure/reconciliation, output/progress failures, cancellation,
cross-root exclusion, worker SIGKILL/orphan exclusion/recovery, comparison
separation, idle accounting, tampering and boot identity. Synthetic controls prove
these engineering mechanisms, not original-game fidelity. The integration
receipt must separately retain actual systemd kill/restart evidence, resource
counters, real approved endpoints and one selected result reproduced from its
manifest. Frozen CI/launcher policy remains unchanged.
