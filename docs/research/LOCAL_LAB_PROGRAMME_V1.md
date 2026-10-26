# Local research programme: experiment catalogue v1

Status: proposed research designs, 25 October 2026. No new experiment is approved
or launched by this document. The [machine-readable catalogue](LOCAL_LAB_EXPERIMENT_CATALOG_V1.json)
contains 24 bounded experiment cards: four existing workload references and twenty
new designs. It is **not a lab manifest**, and the current worker does not load it.
The current accepted checkout, service, private configuration and 24-hour campaign
are unchanged.

## What this enables

Build an evidence-producing queue around concrete questions, then use reviewed
results to select small Rust/browser implementation slices. Each card specifies
its question, inputs, finite cases, controls, retained evidence, dependencies and
claim boundary. A local implementation/review session can pick up a card by ID
without inventing the experiment from scratch. An unattended worker can execute
it only after a protocol and adapter have passed the admission process below.

Prioritize experiments that remove a known decision blocker. A hundred identical
replays improve repeatability evidence but do not answer a hundred new questions.
Report useful new findings, contradictions and narrowed unknowns separately from
regression results and service availability.

The research baseline for this design is checkout
`8ae412aac6377f4bc824fa6f8c29d76c0c79bd99`. The current workload registry supports
only `synthetic`, `regression` and `research-squad`. Older capability/coverage
tables are useful scope inventories but contain stale blanket statements about
Rust support; the recent PC-R1 through PC-R10 records and actual registry govern
specific current capabilities.

The [recorded 24-hour launch](evidence/local-lab-24h-start-v1.json) began on
25 October 2026 at 14:56:45 UTC, with an earliest horizon completion on 26 October
at 14:56:45 UTC (also UK local time on these dates). That is a historical launch
receipt, not a fresh status check. Completion, post-horizon replay and independent
acceptance remain separate requirements. Do not build on, edit, restart or enqueue
competing work in the retained execution checkout during that qualification.

## Proposed order

| Wave | Experiments | Decision unlocked |
| --- | --- | --- |
| 0: existing evidence | LAB-001 RNG; LAB-002 original R10; LAB-003 fixed Bosman; LAB-004 squad set completeness | Establish the exact baseline after the current qualification and required review |
| 1: retained evidence | LAB-005 anomalies; LAB-006 original consumers; LAB-007 slot/sequence matrix; LAB-008 continuation; LAB-009 RNG boundaries; LAB-010 tactical corpus | Narrow the squad/lineup blockers and expand reliable foundation coverage |
| 2: reference capability | LAB-011 complete capture; LAB-012 member lifecycle; LAB-013 file consumption; LAB-014 fresh seed reproducibility | Establish which state and input provenance future experiments can trust |
| 3: game mechanisms | LAB-015 daily deltas; LAB-016 original saves; LAB-017 contracts/transfers; LAB-018 training; LAB-019 detailed matches; LAB-020 quick matches; LAB-021 competition rules; LAB-023 scouting/news | Produce narrow behaviour contracts across the game |
| 4: integration and lifecycle | LAB-022 season boundary; LAB-024 Rust/browser bridge | Deliver independently evidenced player workflows and longer-lived state |

Waves are dependency groups, not dates or an instruction to run all jobs. LAB-024
can accompany each admitted slice; it need not wait for every wave-3 subsystem.
Dependencies are necessary but not sufficient: each card's backend qualification,
exact input identities, decoder, resource pilot and review are also gates.

Recommended first increment: deliver only LAB-005 and LAB-006 adapters/protocols,
then LAB-009. These use retained material and expose specific unknowns without
requiring a new live-game controller. Next review LAB-007/008 and wrap the existing
tactical scripts in LAB-010. LAB-005/006 may reveal that a live transition capture
is necessary; that is a valid result, not justification to invent squad rules.

## First tranche: concrete experiment designs

### LAB-005: complete anomaly accounting

Question: do independent decoders produce the same complete classification for
every captured member slot, including the two invalid and five foreign-club links?

Use exactly the admitted retained image/heap identities in
[the frozen squad protocol](LOCAL_LAB_RESEARCH_V1.md). The existing structural
result is 43 complete reciprocal candidates, 61 total full-table club associations
and 18 associations without valid complete player links. These are prior
observations to reproduce or contradict, not hard-coded filters.

Read all fifty slots in order. For each retain a private row with slot index,
raw link, extent/alignment status, stable staff identity, reciprocal club status,
linked player extent/identity and all applicable anomaly flags. A separate
exclusive classification must partition all fifty rows; overlapping flags must
not be added as though they were exclusive counts. Independently scan every
staff record and retain every association and exclusion. Keep public output to
counts and hashes.

Use two parsers that do not import each other's classification logic. Compare
the ordered ledger, all denominators and the full inverse set. Freeze the
precedence for overlapping invalidity before execution. Missing required capture
extent censors the affected observations and precludes a completeness finding.

Positive control: a complete synthetic fixture with a known expected ledger.
Negative controls: unaligned staff link, duplicate slot, wrong ID, truncated
record, changed backpointer and omitted slot. Inject controls into private copies,
never the retained capture. A decoder disagreement is a successful completed
comparison with verdict different if both decoders ran correctly. A failed
control is failed execution, not a publishable finding.

Deliverable: a reviewed structural ledger and a list of unresolved semantic
questions. It cannot establish that an invalid value is a sentinel, a foreign
association is a loan, or that all 43 records are selectable players.

### LAB-006: identify the original consumers

Start with the two existing bounded code regions documented in
[PC-R10 command research](PC_R10_COMMAND.md): the fifty-slot counter and the
club-checking assignment caller. Pin the specimen, disassembler and instruction
ranges. Record branch conditions, widths/signedness, reads and call targets.

This is a bounded static inventory. Disassembly beyond the two regions requires
a newly frozen range list; discovered addresses become follow-up questions.
Keep named upstream functions as hypotheses. Changed specimen bytes must reject
admission; branch-target and signedness mutations must break the expected facts.

Deliverable: a small table of proven instruction predicates, which of the seven
anomalous entries each predicate could distinguish, and paths still needing dynamic
evidence. No static path is promoted to a whole-call or UI eligibility contract.

### LAB-007 and LAB-008: command boundaries and continuation

The existing admitted dynamic domain is two actual members, slot zero, ordinary
human club, row mode zero and zero cache count. LAB-007 proposes extending the
slot domain; none of the extension is already qualified.

Freeze 20 slots x two choices of first member x three operation sequences:
assign/read; assign/repeat same assignment/read; assign A/assign B/read.
For the third sequence B is the other admitted member. Reset the full retained
state before every case. This is 120 cases, chunked into twelve immutable jobs of
ten cases, with a deterministic case order. Preserve raw effect traces and
unmodified regions; do not assume duplicate removal, position names or swaps.
Treat an unexpected original dependency as censored, never a made-up rejection.

LAB-008 selects one eight-command sequence from the qualified LAB-007 domain.
Compare uninterrupted execution against restoration at each of seven internal
boundaries, with two independently initialized repetitions. Capture the complete
emulator register and mapped-memory state needed by the harness. A missing
mutable component invalidates the claim of complete continuation. Fourteen paired
cases fit two fixed chunks of seven if the pilot confirms the budget.

Independent review must inspect expected effects as well as the oracle; comparing
two outputs from the same flawed model is insufficient. Preserve exact full
state and ordered writes, not just the visible mapping value.

### LAB-009: RNG boundaries inside the existing domain

Freeze the explicit Cartesian product in the catalogue: seven signed bounds,
four cursor positions, two offsets and four CRT states, giving 224 cases.
Keep the qualified synthetic table unchanged. Split into four fixed jobs of
56 cases, with a stable ordering and case-list hash.

Execute actual original instructions, Rust native and WASM for each case. Compare
return values and every exposed state field. Include zero-consumption, last-word
and wrap observations and defective signed-remainder/wrap/extra-draw models.
Checkpoint probes, if added, require an explicit additional case list and count.

This extends sampled boundary evidence; it does not prove the entire admitted
domain. Larger x87 bounds, actual-game tables and OS-time seeding need separate
protocols and cannot be introduced by changing a seed list.

### LAB-010: wrap previously qualified tactical research

Inventory the existing registry, producer and effective-plan qualification
scripts and their exact evidence before writing an adapter. Pin a finite
script/case list, preserving each original domain and its controls. Reuse the
fixed lab adapter interface; never expose an arbitrary script path or argv.
Keep retained and fresh-input branches distinct and retain empty option-3
limitations. This increment produces automation coverage, not new semantics.

## How a card becomes executable locally

1. **Select and freeze.** Choose a stable card ID/version, one falsifiable question,
   exact reference lineage and literal case list. Resolve every missing capability.
   Freeze input/tool/source hashes, expected observations, decision rules, exclusions,
   controls, comparison policy and resource ceilings before a research run.
2. **Implement a fixed adapter.** Work in a separate development checkout. Follow
   `validate`, `validate_job`, `prepare` and `result` in
   [the local lab contract](../architecture/LOCAL_LAB_V1.md). Pin every used file.
   Allow only reviewed parameter values; never interpret catalogue text as commands.
   Build binaries before execution; workers do not edit, compile or generate code.
3. **Review exact source and protocol independently.** A different reviewer checks
   input admission, oracle independence, controls, denominators, all writes,
   censorship, resource accounting and claim scope. Card dependencies alone do
   not grant approval.
4. **Pilot and seal.** Run positive/negative controls and a short real-input pilot,
   measure peak resources and semantic progress, inspect retained artifacts and
   replay one case. Do not choose a hypothesis or discard cases after seeing results.
   A protocol change creates a new version and preserves earlier attempts.
5. **Publish an approved profile.** Add only the accepted template and fixed profile
   to the registry and CLI/Windows choices, with validation and appropriate tests.
   Pin a new accepted execution checkout and configuration. Preserve the old
   checkout/configuration for the current qualification and all existing replay.
6. **Execute and review evidence.** Start the approved profile through the existing
   Windows launcher after the active campaign finishes. Review raw receipts and
   replay independently. Findings may then support a separately reviewed behaviour
   contract, fixture admission and Rust/browser implementation.

These steps are the proposed pickup process; there is no generic
`Lab.cmd Start LAB-005` command today. Existing commands remain
`Lab.cmd Start regression`, `Lab.cmd Start research-squad` and the synthetic
profile. Starting regression runs all three baseline jobs. Do not use it to
interrupt the qualification merely to refresh this catalogue.

A useful future read-only operator addition is List/Explain for card readiness,
missing capabilities and last reviewed evidence. Only registered approved profiles
should have Run enabled. A folder watcher that executes arbitrary JSON is outside
this design.

## Evidence and decision contract

Each future protocol should require a private receipt containing:

- Card/protocol/version, exact case-list hash, manifest hash, source/build/tool/
  input hashes, backend lineage, seed and captured RNG/scheduler state coverage.
- Every planned case and its disposition: completed, rejected, censored, failed,
  cancelled or not started; every physical attempt including interrupted retries.
  Preserve native lab execution enums and record per-case censorship in details.
- Independent execution status, comparison verdict and research conclusion.
  A hypothesis can be contradicted while execution succeeds. A structural question
  with no reference comparison remains not-run, with its hypothesis result separate.
- Per-case observations, expected model if one exists, full controls, raw artifact
  inventory with sizes/hashes, progress and resources, and exact first divergence.
- Replay identity, immutable original/replay result references, independent review
  identity and a scoped claim with remaining unknowns.

Use conclusions supported, contradicted or unresolved only for the frozen tested
question/domain. Do not convert finite-sample support into a universal rule.
For stochastic/mechanism work, freeze complete states and treatments beforehand,
retain paired trajectories, measure RNG-consumption divergence and state whether
independent sampling is actually justified. The proposed small studies are
exploratory; population win-rate or effect-size claims need a separate statistical
protocol with precision/power, intervals and multiple-comparison handling.

Research reports should answer: what question was settled, on which cases, which
controls discriminated, what disagreed, what remains unknown, and what decision
the evidence permits. Counts of named functions or successful jobs are not fidelity.

## Bounds and local scheduling

The catalogue supplies proposed per-attempt budget classes and max logical jobs.
They are admission ceilings, not measured runtimes. Retain one worker, one CPU,
2 GiB memory, no swap and 128 tasks. If capture/emulation/browser work cannot fit,
mark it blocked and separately review the requirement; do not silently raise limits.

For LAB-005/006 the proposal is 300 seconds per attempt, 120 seconds without
semantic progress, 2 MiB streams and 64 MiB artifacts. For the oracle tranche it
is 600/120 seconds, 2 MiB streams and 512 MiB artifacts. At most two attempts,
with retries only for infrastructure interruption. Logical-job completion should
publish progress; stdout or a timer is not semantic progress. Confirm that each
case finishes inside the stall ceiling during the pilot or redesign chunking.

The useful-work upper bound is max_jobs x max_attempts x elapsed_seconds.
For LAB-009 this is 4 x 2 x 600 = 4,800 seconds; it is not an expected duration.
No new catalogue card requests a 24-hour observation horizon.

Disk limits apply per attempt, not to total retained history. Before approving a
batch, reserve worst-case retained growth across all attempts plus the free-space
floor and publication headroom; include private raw captures, stream sampling
overshoot and earlier retained campaigns. If the bound is insufficient, reduce
the frozen case set or defer execution. Never delete failed evidence to make room.
Service failure/rejection and parity divergence stop the campaign at the first
terminal event under the default policy; unstarted cases stay in the denominator.
A false research hypothesis by itself need not be a parity divergence.

Run new batches manually after qualification/replay acceptance and after required
builds have finished. A recurring schedule is a separate owner decision, not part
of this design. Finite approved batches can then run while the chat is closed.

## First implementation handoff

Pick up LAB-005, then LAB-006. Owned implementation paths would be dedicated
research scripts, focused tests, new frozen protocols and minimal
`tools/lab/workloads.py`/CLI registry changes. Acceptance requires exact private
input admission, all-slot accounting, independently checked parser/instruction
receipts, discriminating controls, bounded execution, report integration and one
replay. Do not add production squad state or change accepted v1-v5 save semantics.

After their evidence review, choose LAB-007 or LAB-011/012 based on what the
anomalies and consumer predicates actually show. LAB-009 can proceed independently
once its own oracle/adapter is reviewed. Keep game implementation as a separate
increment using an admitted behaviour contract.

This catalogue is a first programme backlog, not exhaustive whole-game coverage.
Assets/localisation, board/jobs, international football, multiplayer, other
competitions and additional UI workflows still need their own designed cards as
the reference capabilities mature.
