# LL1 retained qualification audit and acceptance procedure

## Final acceptance — 26 October 2026

**Decision: passed for scoped LL1.** The original campaign actually completed at
14:56:45.275969 London after **86,400.014999163 monotonic seconds**, with
`observation_qualified=1`, no stop reason and all three intended jobs succeeded.
All four attempts, including the interrupted first Bosman attempt, remain retained.
Independent final inspection reverified all ninety source/tool/input pins,
configuration identity, boot identity, forty-eight complete inventory entries,
four canonical result publications and the terminal report's exact snapshot.
The original holder recorded its completed `worker-terminal` outcome.

The preserved Windows launcher then ran selected RNG replay
`ll1-24h-20261025-replay-d5be48069850` at 16:02:52.346617 London, after actual
completion. Its one successful attempt completed with `equal`; all eleven
artifact entries and its publication verified. Both native and WASM artifacts
were directly byte-compared to their original counterparts: 75,952 bytes each,
the frozen `1c8d5c5b...97ce0d16` SHA-256 and `[1023,61,2447,123]` controls.
The replay holder also reached `worker-terminal`.

The [final independent evidence](evidence/ll1-qualification-final-20261026-v1.json)
records exact hashes, resource measurements and the private acceptance receipt
digest. The unchanged native admission validator accepted the complete private
receipt and evidence references. This releases the single slot for the separately
approved sequential LAB-005/006 pilots; it does not accept their future results.

Final accounting retains 182.659605 seconds active, 85,172.874857 seconds idle and
1,044.480537 seconds uncredited orchestration, polling, publication and restart
intervals. The residual is not all restart downtime. The original interrupted
attempt's final CPU/memory sample remains unknown. Raw R10 receipt equality,
eleven successful/four censored calls, twelve controls and the fixed Bosman endpoint
were verified; Bosman original-process comparison remains `not-run`. Full P01/P03
and the separate seventy-two-hour gate remain open.

## Historical interim audit — 25 October 2026

25 October 2026. **Decision at that time: incomplete.** The independent read-only audit at
15:56:30 London found the original campaign running, with 3,584.025 of 86,400
monotonic observation seconds recorded. This is neither a pass nor a release of
the heavy-work slot. The earliest horizon is **26 October 2026 at
14:56:45.250062 London time**; the actual terminal state must also be observed.
London is UTC+00:00 at both of these timestamps.

The authoritative frozen protocol remains [LOCAL_LAB_24H_V1.md](LOCAL_LAB_24H_V1.md).
This procedure does not change its endpoints, horizon, budgets or acceptance
requirements. The separate LAB-005/006 operational source review can finish now;
qualification acceptance, pilots, replay and raw-evidence acceptance remain gates.

## Preserved identities and interim findings

- Accepted execution checkout: `/home/derek/cm0102-lab`, clean at
  `42a313887e46274a2932dbe8c04de7a5e8f2840d`.
- Private state: `/home/derek/.local/share/cm0102-lab`.
- Campaign: `ll1-24h-20261025`; canonical manifest SHA-256
  `0ac601252e55b485f5305d433c5f6c68c9d11e64cf07034f2488907061c3d711`.
- Three logical jobs succeeded. RNG and R10 comparison verdicts are `equal`;
  Bosman is `not-run` for original-process comparison. Four physical attempts
  remain visible, including the interrupted first Bosman attempt and its distinct
  successful second attempt. Completed RNG/R10 jobs were not repeated.
- All 90 unique source/tool/input pins, all 48 artifact inventory entries, complete
  directory membership and all four result publications matched their durable
  records. No symlink, missing artifact, changed result or publication error was
  found. Private raw contents were not copied into Git.
- The expected single SIGKILL/restart is recorded. Systemd's journal independently
  records main-process signal 9 and the one restart. The replacement worker and
  holder were active, the holder heartbeat was fresh, and the boot identity
  matched. No observation-gap, boot-change or censorship event existed.
  The durable restart-requested to recovered events span 3.269 wall-clock
  seconds; that interval is not a separate monotonic heartbeat-gap measurement.
- Recorded active time was 182.660 seconds; idle time was 3,347.448 seconds. The
  53.917-second residual includes orchestration, reporting, polling and restart
  intervals. It must not be relabelled entirely as restart downtime or credited
  as useful work. The interrupted attempt's final CPU/memory sample is missing
  by design of crash recovery and stays unknown, not zero.
- The retained eight-case service acceptance receipt matched SHA-256
  `78e127f892e0f1ff85b83afc7b608f088ccb1aa172afc029bc6d978c13be3818`.
  All ten physical attempts in that private drill store independently passed
  complete inventory and canonical result-publication verification. Its receipt
  source is the earlier `ca6d465871d971d0b35e8afaa08925f04cc1e073`, with
  implementation-file hashes and subsequent evidence inheritance recorded in the
  existing delivery/accounting reviews; do not relabel it as a fresh drill on
  the qualification revision.

The [sanitized audit receipt](evidence/ll1-qualification-audit-20261025-v1.json)
records exact counters, hashes and limits. Its kind is
`qualification-interim-audit-v1`, decision `incomplete`. It cannot be supplied as
a qualification acceptance receipt. This audit used a consistent SQLite
`mode=ro` transaction, streaming file hashes, Git reads and service/journal reads.
It did not call `core.snapshot` (which opens the mutable connection), regenerate
reports, signal services, alter configuration or launch replay. The periodic
report can legitimately lag the database snapshot while observation continues.

## Closure after the actual horizon

1. Read the original database consistently and retain a private full snapshot.
   Verify the exact checkout, configuration, manifest and every input/tool pin
   again. Require `state=completed`, `observation_qualified=1`, no stop reason,
   recorded monotonic observation at least 86,400 seconds, matching boot identity
   and a durable completion event after the horizon. A wall-clock deadline alone
   cannot satisfy these conditions. Confirm the worker has exited and the holder
   has recorded its terminal outcome before allocating replay.
2. Account for exactly the three frozen logical jobs and every physical attempt,
   including failures, censoring, retries and publication states. Require all
   intended endpoints: native/WASM RNG equality and four controls; retained R10
   equality with eleven successful/four censored calls and twelve controls; fixed
   fourteen-day Bosman `normal,again` endpoint. Bosman original comparison remains
   `not-run`. Verify all inventory paths, sizes, hashes, complete directory
   membership and canonical published results against the database. Review
   journal/recovery evidence, resource samples and active/idle/residual accounting.
3. After terminal state, refresh and retain the completed machine report and its
   digest. Require its decoded JSON to equal the complete terminal snapshot,
   including every campaign/job/attempt/event field, as enforced by admission. Hashes
   of canonical manifest JSON and the newline-terminated manifest file are
   distinct identities; label each correctly. Pending publication is unresolved
   evidence, and changed publication is an integrity failure, never auto-repair.
4. Run only the selected RNG replay, using the preserved installed Windows
   launcher and its acknowledged lifetime holder. First verify its settings still
   point at the accepted checkout and private state. Do not run Setup or redirect
   it to the LAB-005/006 checkout before qualification acceptance.

   ```powershell
   & "$env:LOCALAPPDATA\CM0102Lab\Lab.cmd" Replay 001-rng-native-wasm-v1 -Campaign ll1-24h-20261025
   ```

   This command is **for after verified actual completion**, not an instruction
   to execute during the running observation. The launch creates a separately
   identified replay campaign and preserves original attempts. Record that new
   campaign identity, manifest, fresh holder acknowledgement and all attempts.
   A direct WSL-only CLI invocation is supervised operation requiring a retained
   foreground WSL client, not evidence of Windows unattended launch.
5. Independently inspect the replay's raw artifacts. Require one selected RNG
   logical job, zero observation horizon, the original source/job/tool/input pins,
   correct `replay_of` linkage, and replay start after original completion. The
   job must succeed with `equal`, publication must be complete, and native.stdout
   and wasm.bin must each contain **75,952 bytes** with SHA-256
   `1c8d5c5b3443386e18f2124f19dcebbde7999124e3b557b71f78507597ce0d16`.
   The four defect-control mismatch counts are `[1023, 61, 2447, 123]`.
   Verify equality directly against both original artifacts, not only result
   summary strings. Attempt IDs, timestamps and resource samples are separately
   reported metadata, not scientific output equality targets.
6. The independent reviewer records a final decision and exact evidence identities.
   Only a passed decision with post-horizon replay acceptance releases the slot
   to the separately reviewed LAB-005/006 pilots. Run those pilots sequentially
   and review their own complete ledgers/facts, resources, controls and replay;
   this LL1 acceptance does not pre-accept their findings or admit LAB-007.

## Decision and release receipt

While observation or mandatory review/replay is outstanding, record `incomplete`
and keep execution blocked. Final outcomes are:

| Decision | Required interpretation |
| --- | --- |
| passed | Actual eligible horizon completed, every intended endpoint and retained publication verified, selected post-horizon RNG replay equal, independent raw-evidence acceptance recorded. |
| failed | A demonstrated endpoint/control divergence, terminal workload failure or integrity violation prevents acceptance. Preserve all failures and identify the failed condition. |
| censored | Boot change, heartbeat gap, interruption or unavailable evidence prevents establishing the required observation. Retain the incomplete run and never credit unobserved time. |

Record both observed failure and censorship facts if both apply; the decision
must not hide either. All non-passed dispositions keep pilot execution blocked.
No existing passing CI check can substitute for these empirical conditions.

The private release receipt consumed by the pilot gate has schema version 1,
kind `qualification-acceptance-v1`, `decision=passed`, an independent `reviewer`
different from `implementation_author`, `observed_at_utc`, the exact
`source_revision`, `campaign_id` and `manifest_sha256` above, and
`selected_job_id=001-rng-native-wasm-v1`. Its `evidence` object contains
`completion_snapshot`, `completion_report`, `replay_snapshot` and
`replay_manifest`, each a private `{path, sha256}` reference to retained bytes.
Snapshots have the complete `core.snapshot` data shape, including decoded
manifest/spec/result/detail objects, jobs, attempts and events. The admission
validator must validate underlying evidence and publications, chronology and
scientific identities; a human-authored `passed` field alone is insufficient.
No such release receipt exists as a result of this interim audit.

Full P01/P03, the separate seventy-two-hour requirement, original-process parity,
complete squad eligibility and production lineup/save semantics remain open.
