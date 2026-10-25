# LAB-005 through LAB-007 development handoff

25 October 2026. This increment implements bounded candidate adapters and
controls; it does not claim completed campaigns. The exact source/protocol
identities and independent review dispositions are retained in the accompanying
`evidence/lab005-007-*.json` records.

| Campaign | Implemented | Execution release | Real pilot / replay / raw acceptance |
| --- | --- | --- | --- |
| LAB-005 | Two separate decoders, full ordered slot/staff/player accounting, controls, exact private comparison and sanitized reports | Blocked | Not run / not run / pending |
| LAB-006 | Fixed PE/disassembler endpoint, two bounded ranges, detailed instruction inventory and controls | Blocked | Not run / not run / pending |
| LAB-007 | Deterministic 120-case definition in twelve groups of ten; admission blocker report | Not admitted; no executor | All 120 unstarted; zero attempts |

Independent source review is a separate gate from execution approval and raw
evidence acceptance. No structural counts have been newly reproduced or
contradicted. In particular, 43 candidates, seven anomalies and 61 associations
remain earlier observations. No real pilot CPU, memory, disk or stall measurement
exists for these candidates. Synthetic test durations are not pilot measurements.

## Live prerequisite and preservation

The lead read the actual accepted worker status, service state and Git identity.
`ll1-24h-20261025` was still **running**, with all three useful jobs succeeded and
four physical attempts, at 2,313.027 recorded observation seconds. Its manifest
SHA-256 was `0ac601252e55b485f5305d433c5f6c68c9d11e64cf07034f2488907061c3d711`.
The qualification checkout remained clean at
`42a313887e46274a2932dbe8c04de7a5e8f2840d`. The `observation_qualified=1` field means
eligible so far, not completed or independently accepted. This is a timestamped
inspection record, not future live status.

The horizon cannot finish before 26 October 2026 at 14:56:45 London time; actual
monotonic observation, post-horizon selected RNG replay and independent review
remain mandatory. No qualification process was stopped, restarted, signalled or
reconfigured. No build or new retained-input pilot ran. Its private configuration,
inputs, earlier results and replay checkout were preserved. Development uses
`lab-005-007-dev` on `codex/lab-005-007-bounded`, separate from `review-source`
and the accepted WSL execution checkout. The two original untracked programme
documents in `review-source` were copied without modifying their originals.

## Supported commands and their current disposition

The development checkout supports read-only readiness without private config,
systemd access, or a worker:

```sh
python3 tools/lab/lab.py readiness
```

From PowerShell, without changing the installed launcher's accepted target:

```powershell
wsl -d Ubuntu -u derek -- python3 '/mnt/c/Users/derek/OneDrive/Documents/ChatGPT/CM Simulator PC/lab-005-007-dev/tools/lab/lab.py' readiness
```

`Lab.cmd Readiness` is implemented for a future launcher installation pointing
at this reviewed revision. Do not run Setup to redirect the existing launcher
while qualification/replay still uses its accepted target.

Ordinary candidate `start` names still **deliberately reject** before private
input access or job creation:

```sh
python3 tools/lab/lab.py --root /PRIVATE/NEW-STATE start research-anomalies
python3 tools/lab/lab.py --root /PRIVATE/NEW-STATE start research-consumers
```

The [operational admission procedure](LAB_005_006_OPERATIONAL_V1.md) now provides
`freeze` for the separate native-WSL checkout and private configuration. It binds
exact inputs/tools/source, applies the structural ceilings and physically reserves
pilot/retry/replay disk capacity without configuring or executing a job. After
independent exact-revision and actual-manifest review, `admit` additionally requires
the accepted completed qualification and selected RNG replay evidence. Global
and per-job validation enforce the same gates, so an arbitrary manifest or a
configuration flag cannot bypass them. There is no LAB-007 launch command.

The existing supported report and replay interfaces remain:

```sh
python3 tools/lab/lab.py --root /PRIVATE/STATE report CAMPAIGN
python3 tools/lab/lab.py --root /PRIVATE/STATE replay JOB --campaign CAMPAIGN
```

For a frozen LAB-005 profile the job identity is
`001-research-squad-anomalies-v1`; for LAB-006 it is
`001-research-member-consumers-v1`. These identities are frozen execution targets,
not existing results. No LAB-005/006 result is currently replayable. Run the
qualification's existing report/replay only from its preserved accepted checkout
and configuration, with replay after actual horizon completion. Replay must
create a separate campaign and never replace original results.

## Evidence and remaining work

Future immutable attempt artifacts are `lab005-private/decoder-a.json`,
`decoder-b.json`, `controls.json`, `comparison.json`, retained failure files,
`lab005-result.json`, and `lab006-private.json` / `lab006-result.json`. The lab
adds manifests, complete physical-attempt history, logs, resource samples and
artifact inventories. Raw ledgers and instruction facts must stay private.
Public summaries expose counts/hashes and separate execution, comparison and
hypothesis fields. Missing state and dependencies remain explicit unknowns.

The selected-result replay must reproduce deterministic scientific ledgers and
fact hashes, with timing/attempt identities reported separately. Review raw
controls and exclusions independently before accepting any finding. LAB-007's
smallest next experiment and full admission conditions are in
[its blocker report](LAB_007_BLOCKERS_V1.md). No original UI, whole-squad
eligibility, loan/sentinel interpretation, production lineup/save semantics or
LAB-008 work is admitted by this increment.
