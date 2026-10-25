# Programme progress

Updated 25 October 2026. Current task queue: [PC delivery plan](../roadmap/PC_FIRST.md). Earlier merges and detailed attempts remain in the [pre-reset Git record](../history/README.md); they are historical evidence, not a requirement to repeat all setup.

## Demonstrated evidence

| Area | What is established | Limit |
|---|---|---|
| B0 inventory | Deterministic importer; 11,747 function starts, 6,863 named rows and 4,428 globals; PE-backed address validation | Names are hypotheses, not verified game semantics |
| Official inputs | Exact official executable and separate 760-file clean set rehashed during PC review | Modified installed folder stays separate; staging does not prove a process consumes clean data |
| B1 / PC-R2 Bosman | Fresh fixed-clock seed-1 two-run 14-day replay passed in 116.900 seconds including input verification; qualified retained binary rehashed | Same-save endpoint only; comparison not-run; no original parity |
| Comparator | Synthetic A/A and deliberate divergences exercise comparison mechanics | No qualified real original/Bosman bundle or parity verdict |
| Windows host | Two complete retained probes accepted as stable; fixture and Stage 2 no-UI builds accepted | Fixture UI/production launchers/original have not run in the Lab's qualified route |
| PC-R0 Reversal recovery | Root retained checks passed; fresh official-instruction RNG oracle and synthetic table byte-match retained files | Scoped synthetic state/table; no full initialization, original game process or save compatibility |
| PC-R1 Rust RNG | 1,024 CRT steps, 2,570 bounded calls, 512 checkpoints and 511 restored continuations; executed native/WASM bytes identical; four defect controls detected | Explicit synthetic table/state domain; excludes seeding, x87 large bounds, actual tables and original saves |
| PC-R3 Rust/browser | Original-instruction 24-case plan-index setter qualification; 37-operation native/Chromium state/event equality; React Apply/Export/Import and corrupt-import rejection | Fictional squad/labels, preinitialized null-owner clubs, option zero; original UI/plan contents/match effects unqualified |

Supporting records: [B0](B0_MAP_IMPORT.md), [input qualification](P00_INPUT_QUALIFICATION.md), [Bosman build/replay](B1_BOSMAN_BUILD.md), [smoke observations](B1_CLEAN_SMOKE.md), [Windows host](P02_ORIGINAL_HOST_QUALIFICATION.md), [Reversal receipt and boundaries](../research/REVERSAL.md).

Historical setup failure: the 3.7 GiB/no-swap VPS could not complete the Bosman build. The PC/WSL build did complete (11m19.72s, peak RSS 7,547,840 KiB). The old VPS sizing constraint is not the current PC's specification. No VPS upgrade or continuous campaign is scheduled.

## Accepted PC delivery increment

[PR #32](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/32) carries the reviewed implementation, exact final-head CI and merge identity. Implementation code revision `80a2cb6ca6afaa8db6221b441b9fb7cdcedbf20f` passed independent GPT-6 Astra/high review after fixing initial WASM buffer growth and public-world invariant bypass. Two GPT-6.1 Sol/medium workers delivered R1/R2; the coordinator delivered and integrated R3. Review rotation and one-heavy-job ownership were observed. Actual aggregate token/billing totals are unavailable.

The pinned Rust 1.99.1 toolchain (fmt/clippy/WASM) is operational on WSL-native checkouts. Nested Bosman output capture now has incremental caps/deadline. Admitted supervisor failures retain canonical request, capped streams and a failed replay manifest when publication succeeds; storage failures remain explicit. All 53 lab tests pass, alongside five RNG/management tests and one compile-fail boundary test. Formatting, workspace Clippy with denied warnings, builds, TypeScript strict typecheck and real-browser interaction pass. The earlier R2 summary's total was corrected from 51 to the category sum of 53; no reference outputs changed.

Receipts and precise scope: [R1](../research/PC_R1_RNG.md), [R2](../research/PC_R2_RECOVERY.md), [R3](../research/PC_R3_MANAGEMENT.md). New synthetic oracle data and attributable research are public; original binaries/data/captures and replay inputs stay private. Historical control checkouts and frozen CI/launcher contracts are preserved.

## Manager-bound management extension

[PR #33](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/33) records
exact final-head review, CI and merge identity. Three actual ordinary-club / AI
manager record pairs were recovered from retained older instrumented Bosman
state. The +0xcf field is a manager staff pointer, not ownership. The official
original instructions pass 21 connected setter/resolver/getter cases (63 calls,
153 starts) over this state, with only admitted mapping words changed. Both
banks resolve correctly. Human-reserved IDs and diagnostics remain outside scope.

Rust now admits exact reviewed private/public-regression fixture fingerprints,
supports sparse club IDs, projects bank locations, and validates version-2
save/reload with continuation and deduplication. Legacy version-1 exports still
round-trip byte for byte. React supports club selection, manager context and
explicit private-reference import, with controls locked during import reads.
All 105 native/Chromium operations match; 63 Rust tests, five extraction controls,
format/lint/build and strict TypeScript checks pass. Evidence and exclusions:
[original path](../research/MANAGER_BOUND_PLAN.md),
[input recovery](../research/PC_R3_CAPTURE_INPUT.md),
[browser receipt](../research/evidence/pc-r3-manager-browser-v1.json).

The retained source tree matches all 760 clean-manifest entries today. There is
no contemporaneous consumption seal for the older capture. This supports the
bounded official-instruction/state qualification; it does not certify a current
Bosman platform, original Windows process or full human-manager workflow.
Private records, names and inputs stay out of Git. Research/review used Astra/high;
bounded recovery used Sol/medium, with compact handoffs and one heavy local job.

## PC-R4/R5/R6 delivery

Work started from refreshed main `d769ce7` in separate WSL worktrees with two
workers and one explicitly rotated heavy-job slot. [Ownership/dependencies](../roadmap/PC_FIRST.md)
retain actual model routing; token/billing totals are unavailable.

R6 current-profile storage merged in [PR #34](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/34),
merge `3248e75b12a06919504c743c54dcedb1255af21f`. Independent Astra/high review
of final head `762ed06` verified a failed-initial-recovery retry fencing fix.
All four frozen checks passed. Atomic IndexedDB publication, previous-valid
fallback, accepted-versus-durable reporting and session/tab fencing pass actual
persistent Chromium recovery/failure controls. Quota/denial exceptions are API-
injected; actual disk exhaustion and power-loss guarantees remain unqualified.

R4 now implements direct human registry slot 0/1 selection over an exact reviewed
real preinitialized reciprocal binding. The ordered effect is one `+0x9a69` byte
write; the distinct slot stride is 7,885. Original instructions pass 21 calls/
345 starts on retained complete state and 21/290 on fresh sparse state without
stubbed callees. The retained outer getter's fallback and fresh registry branch
remain distinct. Coordinator independently reproduced both receipts byte for
byte. Full constructors/appointments, original UI and match effects stay outside
scope. The fresh projected fingerprint was unadmitted in that delivery;
the separate follow-up below records its subsequent admission review.

Integrated validation passes 70 Rust tests, five oracle controls, formatting,
workspace Clippy/build, WASM and strict TypeScript checks. All 159 native/actual-
Chromium operations match, including human v3 commands, effects, save/replay and
deduplication; old 105 cases and v1/v2 compatibility remain unchanged. Browser
persistence now recovers all five admitted profiles with exact native continuation.
[R4 evidence](../research/PC_R4_HUMAN_REGISTRY.md) and
[R6 storage](../research/PC_R6_BROWSER_STORAGE.md) retain receipts and limits.
R4 delivery merged in [PR #35](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/35),
merge `8fa4af9e5bfe6e96a81ef58c8e75fc377b2b9f98`. Final head
`454eb70c58b5c12beed15a5f7632a3514ad11dd3` passed all four frozen checks.
Coordinator and Sol/medium independently reviewed worker-authored core/oracles;
Astra/high independently reviewed coordinator-authored UI/storage integration.
No final findings remain; the earlier misleading legacy limitation was corrected.

R5 separately executed the reviewed minimal observer: four bounded 14-day arms
completed in 339.91 seconds with contemporary seals. All four endpoint saves
match exactly, and two complete sparse human-state captures match byte for byte.
Independent official-instruction replay passes on that captured read set. The
[R5 contract/receipt](../research/PC_R5_CAPTURE.md) retain exact source, derivative,
tools, clean inputs, commands, configuration, timing and output identities. Eight
failure controls pass, including closed-stream hang, incomplete extents, overlap,
output limits and invalid pointers. Coordinator reviewed observer/driver `e36b516`
before execution, then independently verified the actual private/public artifacts,
all seals and fresh oracle/build/capture link. Only the console privacy summary
and one observer trailing-CRLF normalization changed after execution; exact
executed source identities remain retained. Final review caught the formatting
warning and the complete delivery diff passed after normalization.
[PR #36](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/36) merged as
`c32436a5b6d4e76d70ca2b551af6dc56c61cbca3`. Exact final head
`446f909951798f71e828ac225b374cd6a9ea669e` passed independent coordinator and
Astra/high review, all four frozen checks and the affected eight controls after
refreshing against the R4 merge. All three bounded increments are delivered;
the active WSL checkout and clean Windows review mirror were refreshed to this
merged implementation. Actual data opens were not independently observed;
consumption remains unknown and comparison remains not-run. Endpoint equality
does not claim whole-runtime noninterference. No original Windows process ran.

## Fresh human fixture admission follow-up

Independent review from main `7665cec` approves the exact fresh 481-byte human
projection `15697cf…` for the existing direct slot 0/1 command, captured origin
and v3 format. The retained real fixture remains admitted and old saves remain
unchanged. The reviewer authored neither R4 nor R5, reconstructed the projection
without either existing parser, checked sealed source/build/tools/input/output
identities and reproduced both original receipts byte for byte. The private audit
and projection script are hashed in the [admission decision](../research/evidence/fresh-human-fixture-admission-v1.json).

All 204 native/actual-Chromium operations match, including 27 fresh oracle/UI
cases and 18 fresh/retained identity/save controls; the previous 159 hashes remain
unchanged. Actual browser close/reopen recovers all six fixtures with exact save,
events/deduplication and native continuation. Fresh corruption/transaction-abort
and same-profile/session delayed/stale-write cases pass. The previous five stored
state/save results remain exact. Existing quota/denial injection limits remain.
All 71 Rust tests pass serially, plus formatting, workspace Clippy, native/WASM
builds and strict TypeScript/build. An initial parallel run failed three unchanged
supervisor timing assertions; no thresholds, runtime source or frozen CI changed.
Delivery merged in [PR #38](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/38),
merge `d1df089e6521113afda787be2d20340c17ea99de`. Independent Astra/high review
approved exact head `21eed5453282e0904902c626d2a3386450f9fcc1` with no findings,
independently repeated all 16 management tests and verified receipts/legacy hashes.
All four frozen checks passed, including the unchanged default parallel Rust CI
run. The initial local parallel timing failures remain retained; no threshold or
CI policy changed. The additional exact fixture is admitted with no open delivery
dependency; fidelity exclusions below remain unchanged.
Evidence: [scope and browser/recovery receipts](../research/PC_R4_HUMAN_REGISTRY.md#independently-reviewed-fresh-fixture-admission).

## Additional human registry producer

Independent qualification and raw projection review approves the exact retained
and fresh schema-2 wrappers plus a separately labeled synthetic regression. The
additional fixed option-2 producer writes one byte at `+0x9b25` for values 0/1,
including repeats, while preserving the selected slot, immutable DWORD guard and
other captured state. Both official oracles pass 37 calls/186 distinct starts,
ABI and complete-state checks, mixed checkpoint continuation and twelve defect
controls; three unsupported probes and the initial harness failure remain explicit.

Rust owns an additive v4 world/save with both commands, shared revision/retry
history and full replay validation. Existing v1/v2/v3 saves retain exact behavior
and bytes without migration. Thin admitted-profile browser controls persist through
the existing storage contract. All 375 native/Chromium operations match; previous
204 hashes and six stored results remain exact. Actual browser close/reopen and
native continuation pass across nine fixtures, plus v4 corruption fallback,
visible actual transaction abort and same-profile retained/fresh writer fencing.
All 79 Rust tests pass serially, formatting/Clippy/native/WASM/TypeScript/build
pass, and no integration failure occurred. Frozen CI is unchanged.

The [decision, independent audit identities and receipts](../research/HUMAN_REGISTRY_PRODUCER.md)
retain the exact scope: neutral option meaning, initialized binding only, no
implicit outer lookup, original UI/lifecycle/appointment/match/original-save claim.
No original process or new Bosman campaign ran. Independent final-head review,
protected checks and merge disposition are recorded in the delivery PR.

Delivery merged through [PR #40](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/40)
as `37c511dc2ec6ca0e173b36a900b09411e1da952b`. Independent review approved
exact head `c53692921af108d37be3493cd934dfb7ddcdebd3` with no findings after
reviewing all 23 files, independently passing 24 management checks and verifying
all receipt/audit seals, 60 relative links and unchanged legacy results. Private
final review: 3,099 bytes, SHA-256
`d61f1e8f1905d33c32318d9bbc762a5024a10f9fa3c0aa30434f774fac27bcbc`.
All four frozen checks passed before merge: Rust run `40189853461` and latest
base-guard run `40189976662`. The target remained `8bd8368` and the reviewed head
was unchanged at merge. Default parallel Rust CI passed; no thresholds/policies
were altered. The additional producer is admitted and delivered within its
documented initialized-state domain. Fidelity exclusions below remain open.

## Remaining engineering

1. Direct human registry selection and the fixed option-2 byte producer are qualified for the retained and freshly captured pinned initialized bindings. General registry construction/load/reuse, appointments, remaining slots/options and original UI/match effects remain unsupported. Next bounded research can qualify a further producer or dependency without assuming gameplay semantics.
2. Original Windows startup, clean-data consumption, A/A and original/Bosman comparisons remain separate medium-helper gates. No original process was launched.
3. Actual-game RNG table qualification, full initialization/seeding, x87 large bounds, original saves and complete match behavior remain open.
4. Browser checkpoint recovery is bounded and tested; cgroup/lease/resource fencing, durable orchestration, physical-storage exhaustion and unattended campaigns remain unqualified.
5. Dormant launcher retirement requires a separately reviewed policy transition; frozen controls were not weakened.

These three accepted bounded increments do not complete the simulator, P02/P04 whole-phase gates or unattended-operation qualification.

## Repository reset

This change removes duplicate bootstrap/implementation plans and the superseded planning review from the current tree, records their Git history, and makes one PC plan authoritative. It corrects the stale Explorer-token-duplication instruction, separates demonstrated results from plans, and adds the pinned Reversal reproduction receipt. Existing Rust/C#/Python source, input locks, private data and frozen CI/launcher contracts are preserved.

Cleanup verification, independent review and merge disposition are tracked in [PR #31](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/31), based on `196d064a0bd8e9ecc152595f8bb438d879b159bc`. The PR records the exact reviewed head, CI runs and final merge identity. Local documentation checks resolved all 155 relative links and verified the receipt against the pinned Reversal artifact hashes; existing source/config/workflows have no diff. A passing cleanup does not mean the runner gaps are fixed, the local Rust toolchain is installed, or implementation has restarted. No whole-game phase is closed by this reset.
