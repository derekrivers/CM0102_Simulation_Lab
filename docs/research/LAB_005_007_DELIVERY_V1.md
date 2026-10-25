# LAB-005 through LAB-007 development handoff

25 October 2026. This increment implements bounded candidate adapters and
controls; it does not claim completed campaigns. The exact source/protocol
identities and independent review dispositions are retained in the accompanying
`evidence/lab005-007-*.json` records.

## Operational preparation completed, execution waiting

The independently reviewed operational revision is
`70def1244f01bf917aa112ee9e98d5922b864489`. A clean detached native checkout at
`/home/derek/cm0102-lab005-006` retains that revision for both pilots and replay.
The separate private root `/home/derek/.local/share/cm0102-lab005-006` contains
`lab005-frozen.json`, `lab006-frozen.json` and their independently authored
`lab005-operational-review.json` / `lab006-operational-review.json` receipts.
Seventeen LAB-005 pins and fifty-four LAB-006 pins were independently verified.
Each profile has 536 MiB physically reserved for its pilot, one selected replay,
bounded infrastructure recovery and explicit disk headroom: 1,072 MiB total.
There is no candidate campaign database, job or physical attempt yet.

The [operational review record](evidence/lab005-006-operational-review-v1.json)
binds the exact source, actual manifest hashes, allocated blocks and private
receipt digests. Its approval is conditional on separate LL1 acceptance; it is
not permission to execute while qualification remains incomplete. The lead's
seven existing workload tests passed in the native checkout, in addition to the
implementation's nine admission, eight candidate and twenty-one isolated core
tests. The reviewer independently repeated the nine admission and eight candidate
tests and verified that the actual interim qualification receipt rejects.

The [qualification audit](LL1_QUALIFICATION_ACCEPTANCE_V1.md) found all ninety
input/tool/source pins and forty-eight long-run artifact entries intact, with
all four attempt publications verified. The latest lead preservation check at
16:07:18 London still found qualification running at 4,232.938 monotonic seconds;
both execution checkouts remained clean. No selected qualification replay or
final acceptance has occurred. The existing daily 16:00 London follow-up now
coordinates qualification closure, sequential LAB-005/006 pilots and replay,
independent raw-evidence acceptance and PR #48 delivery. It stays quiet while
there is no actionable change. The persistent worker remains the execution engine.

Do not advance the native execution checkout to later evidence-only PR commits.
After actual qualification acceptance, follow the
[operational procedure](LAB_005_006_OPERATIONAL_V1.md) to admit each frozen
manifest and use the separate Windows launcher/holder. Keep PR #48 draft until
the remaining empirical and repository delivery gates pass. LAB-007's 120 cases
remain unstarted; the admission decision awaits accepted LAB-005/006 findings.

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
