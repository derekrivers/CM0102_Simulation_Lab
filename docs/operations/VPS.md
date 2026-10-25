# VPS deployment and 24/7 operation plan

> Deferred operational design. The PC is the primary host; no VPS upgrade, deployment or continuous pilot is scheduled.

Status: deferred from the immediate critical path. The PC is the primary host for local B2 calibration and the first B3/P04 slice. This document remains the future B4/P01 durability and continuous-operation design; VPS sizing, the 24-hour pilot, and resource improvements do not block the active [PC medium-helper route](../architecture/PC_MEDIUM_HELPER_QUALIFICATION_V1.md).

No deployment occurred during planning. Host specification, access, budget and original inputs are not yet supplied. The design assumes an existing Linux x86-64 VPS; verify architecture, OS, available disk/RAM/CPU, noisy neighbours, provider sustained-CPU policy and other workloads before selecting limits.

## Sizing by measurement

Start with one simulation worker. A provisional pilot envelope is 4 vCPU / 8 GiB RAM with at least 80 GiB genuinely free workspace; a more comfortable multiworker host may need 8 vCPU / 16–32 GiB and 200+ GiB. These are planning envelopes, not capacity promises or purchase recommendations. All-nation long saves may be several GB; measured trace/snapshot retention often dominates disk. Use existing capacity first.

Worker count = min(CPU admission slots, floor((available RAM - OS/control reserve)/measured p95 worker RSS), disk-safe slots). Keep at least 25% RAM reserve initially and a separately budgeted control plane. Measure CPU-seconds per game-day, p50/p95 run times, RSS/heap peak, save size, write volume, trace amplification and sustained CPU steal. Benchmark one, then two workers; only increase if useful throughput improves without determinism or host-health regressions. No 'games per day' promise before a pilot.

On ARM, qualify a native Bosman build and test results first; an x86 Windows reference may remain remote. Do not assume cross-architecture emulation has acceptable throughput or identical behaviour.

## Services

Compose services: PostgreSQL, lab API/scheduler, bounded worker service, optional dashboard/static server. Systemd starts the stack after reboot. One active scheduler leader uses a database lease; workers are individually fenced. Containers get explicit CPU/memory/PID limits verified on the actual host (Docker defaults are not limits). Job processes run under a non-root identity with read-only input mounts and private writable attempt directories. Workers cannot mount the Docker socket or hold repository write credentials. A narrowly scoped supervisor controls allowed backend images/processes.

Initial access through SSH port forwarding/private binding; no public unauthenticated lab API. Database stays private. Separate deployment credentials from research inputs/model tokens. Network is disabled for simulation children unless a specific baseline feature test needs it. Do not place the production research worker on an untrusted public-PR self-hosted runner.

Builds are explicit pinned artifacts. Deploy a tested digest, drain current jobs and retain the previous digest for rollback. Never `git pull main` on every job. Original Windows calibration uses a separate worker/VM with its own measured environment; a Linux VPS alone does not establish original Windows parity.

## Autonomy levels

A0 manual runs; A1 automatically replay approved finite campaign; A2 replenish approved coverage/parameter templates; A3 propose new hypotheses/scenarios for review. The first continuous deployment is A1. P3 may enable A2 after validators and resource caps pass. AI-generated code/scenarios are reviewable proposals, not production deployment authority. Experiment approval is a reusable campaign/template policy, not permission per run.

## Resource and retention defaults

One active CPU-heavy job initially; one Ghidra analysis at a time in a separate budget. Set per-class wall timeout, no-progress timeout, memory and artifact limits from P1 measurements. Use simulation date/event counters plus heartbeats to detect stalls. Pause new admissions at 80% artifact-volume usage, stop new work and preserve recovery capacity at 90%; tune actual byte reserves to max save/trace size. On memory pressure, stop admissions before relying on host OOM killing.

Keep accepted contracts, their minimal supporting reproducers and release regressions indefinitely within backup policy. Keep full unique failure bundles initially 30 days, ordinary successful raw traces 7 days, compact summaries 90 days; expire only when no retained claim/release references them. These are proposed defaults. Deduplicate large fixtures by hash; reference-count reachability through manifests, with a grace period before GC. Diagnostic tracing is bounded and sampled. Daily artifacts must fit the budget before running unattended.

PostgreSQL and artifacts are backed up together with a manifest/checkpoint so references can be restored consistently. Initial RPO target 24h and RTO target 4h; verify by restoring to a separate directory/database, not just observing a backup command exit. Store at least one encrypted backup outside the VPS if available; local snapshots alone do not survive host loss. Until off-host destination exists, report durability as incomplete.

## Failure drills before unattended certification

Kill worker mid-run; kill scheduler after claim; interrupt DB connectivity; expire lease with old worker alive; reboot host; cancel a hung process tree; fill a test quota; corrupt an artifact; interrupt save publication; restore backup. Confirm no stale result overwrites, no partially published success, no lost accepted evidence and bounded retry. Same-input replay after restart must agree at the declared comparison level.

P01 gate: a 24-hour pilot meeting the successful-endpoint and recovery criteria in the verification plan. P03 continuous-operation gate: a 72-hour bounded campaign, reboot/recovery drill and the P02 calibrated A/A corpus. This runs alongside early Rust work and is not a prerequisite for local slice development. A fault found by the game is a successful research result if captured correctly; a missing artifact or false pass is a lab failure.

## Daily operator view

Show running mode/backend/build, current game date/event, last progress time, queue wait, attempts/retries, failed/censored counts, disk forecast, RAM peaks, replay success, original-calibration coverage, new branch coverage, accepted versus pending claims and compute/model spend. Provide pause/drain/cancel/replay/download-reproducer controls with an audit log. Colour coding never substitutes for a clear verdict and reason.

External notifications are optional deployment configuration. The base plan writes daily reports locally in the lab; no messages are sent by this planning work.
