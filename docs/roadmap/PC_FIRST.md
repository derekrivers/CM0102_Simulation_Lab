# Active delivery plan: PC-first reconstruction

Decision: 25 October 2026. The owner accepted the PC review and Reversal reuse recommendations. This replaces the opening implementation sequence and bootstrap planning. It does not close any whole-game phase gate or authorize live Windows execution.

## Outcome and ordering

Build one original-instruction-backed Rust RNG slice, execute the same corpus natively and in WASM, and prove checkpoint continuation. Then deliver one bounded stateful management workflow. Simulation Lab remains the implementation repository; [Reversal](../research/REVERSAL.md) is a pinned research source. Rust owns behaviour; React/TypeScript owns presentation.

| Package | Status | Demonstrable target | Dependency |
|---|---|---|---|
| PC-R0: evidence recovery | Complete for the selected RNG input | Retained research checks pass; fresh official-instruction oracle and synthetic table match retained hashes | Receipt in the Reversal evidence record |
| PC-R1: portable RNG | Verified scoped implementation | 1,024 CRT steps and 2,570 bounded calls match every exposed result/state field; actual native/WASM equality and checkpoint continuation | PC-R0 and a working pinned toolchain |
| PC-R2: reference and lab recovery | Targeted recovery verified; wider reference gates open | Fresh bounded Bosman replay; reconciled evidence ledger; qualified Windows observations when needed | Each claim's own source, specimen and execution prerequisites |
| PC-R3: player-visible stateful workflow | Bounded tactical-plan workflow verified | One evidenced management command, invalid-action rejection, native/browser equality, save/reload continuation | Relevant PC-R1/PC-R2 evidence and an accepted command contract |

PC-R1 may proceed before full P02 calibration and the Windows helper campaign. This is a scoped numeric implementation, not formal P02/P04 closure. Original-process and broader journey claims still require their corresponding gates. B0/B1 remain historical checkpoint names; B2 calibration and B3 reconstruction continue through these packages. B4/B5 continuous operations stay deferred.

## PC-R1 acceptance contract

Use the pinned Reversal CRT generator at VA `00946a04` and small-bound branch at VA `0090cfc0`. Addresses identify the original specimen; they are not Rust pointers. Inspect source/disassembly and original-instruction outputs, not TypeScript alone.

Implement one small portable compatibility crate or module. Inject the 51,000-word synthetic table and explicit fixed-width state. Keep filesystem, clock, processes, database and ambient randomness outside the library. The existing Linux lab supervisor is a host adapter and must not become a WASM dependency.

Admitted corpus: sampled signed bounds within -65,535 through 65,535, CRT wrapping arithmetic, zero-bound no-consumption, cursor increment/wrap and CRT offset update. Freeze supported cursor, offset and table-value domains before coding. Invalid states and unsupported inputs must fail without partial mutation. A sampled corpus is not exhaustive proof of the domain.

- [x] Review the routine contract against the pinned original instructions and oracle; preserve attribution and artifact identities.
- [x] Match all 1,024 CRT steps and 2,570 bounded calls, including exposed state fields and sequential stream checkpoints.
- [x] Demonstrate that negative controls detect wrong wrap, extra CRT consumption, zero-bound mutation and wrong arithmetic; reject unsupported bounds, state and table inputs.
- [x] Execute the same Rust corpus natively and through WASM, comparing canonical output/state hashes. Building WASM alone does not pass.
- [x] Export/reload a versioned Rust RNG checkpoint including table identity, and demonstrate identical continuation. This is not original saved-game compatibility.
- [x] Pass formatting, lint, relevant build/behaviour checks and independent review of the exact revision. Retain commands, tools, hashes, scope and review outcome.

Excluded: large-bound x87 branch, OS-time seeding, full initialization, actual-game table qualification, original-save restoration, additional random sources, original-process equivalence and match outcomes. Preserve source/oracle contradictions as failures; do not adjust expected values to suit the port.

## PC-R2 acceptance and outstanding engineering

- [x] Establish a WSL-native development checkout and pinned toolchain, preserving historical controls and private evidence. Exact Rust 1.99.1, rustfmt, clippy and the WASM target are installed; active work uses separate WSL-native checkouts.
- [x] Reproduce the accepted fixed-clock, seed-1, 14-day Bosman replay with fresh artifact identities before using that deployment for new claims. Rehashing old artifacts is not a new replay.
- [x] Reconcile research by executable hash, RVA and scoped behaviour. Do not add Reversal's 9,241 inferred functions to the map's 11,747 starts as a coverage total.
- [ ] Recover/hash private capture inputs when an experiment needs them; public metadata alone does not reproduce Reversal's live GDI result.
- [ ] Qualify required official Windows observations under the [PC medium-helper contract](../architecture/PC_MEDIUM_HELPER_QUALIFICATION_V1.md). Keep synthetic fixture, original launch, clean-data consumption, A/A and Bosman comparison as distinct gates.

The two identified defects are fixed and tested: nested output is streamed through independent caps/deadline, and admitted failures publish bounded streams/request plus a failed manifest when storage permits. Pre-admission rejects create no attempt; publication failure can leave an incomplete attempt. See [PC-R2 evidence](../research/PC_R2_RECOVERY.md). Cgroups, leases and unattended campaigns remain outside this increment.

The dormant launcher retirement is a separate maintenance task: identify its frozen source/config/contract and workflow dependencies, propose replacement verification, and use the repository's authorized review/protection process. Do not weaken or bypass the base-branch workflow guard to delete it. This task does not block PC-R1 under existing checks; changes to CI itself need that policy transition.

## PC-R3 acceptance contract

Select one original-evidenced stateful squad command after examining dependencies (lineup assignment only if tractable). Freeze the supported state, effects and rejection cases before implementation. Reuse selected Reversal layouts only where useful.

- [x] Display a validated supported squad fixture and perform the command through Rust; an invalid action leaves state unchanged.
- [x] Match native/browser state and ordered events, then save/reload and prove deterministic continuation.
- [x] Keep unsupported commands unavailable and distinguish fictional demo data from captured reference data.

A read-only profile, static match phases or a navigation mock-up does not complete this target. If the chosen action is too coupled, record the evidence and select another bounded stateful action.

## Resource and progress rules

Windows hosts the separately reviewed operator-launched reference route; WSL hosts Linux builds and research. Use native filesystems for active builds, keep private inputs outside Git and live Windows packages outside OneDrive. Initially allow one heavy build or simulation at a time.

No VPS upgrade/purchase, 24/7 campaign, distributed workers, dashboard project, PostgreSQL deployment or Jev pipeline is scheduled. Reconsider infrastructure only when a demonstrated feature or experiment needs it. After two focused setup sessions without useful execution, record the blocker and reassess a simpler route before adding infrastructure.

Measure accepted behaviour contracts, reproducible cases, unresolved divergences and working workflows. Record engineering/model spend when available. Do not use PR counts, named-function percentages or synthetic UI breadth as game completion. Estimate subsequent work after several measured slices; no whole-game completion date is committed.

## Active ownership and dependencies — 25 October 2026

Base: main `084c8ab`; refreshed with origin before work. One coordinator and two workers maximum; one heavy build/replay slot, allocated initially to R2 toolchain setup. All active work is on WSL-native filesystems; historical Windows and Linux controls/private inputs stay preserved.

| Owner | Branch / checkout | Owned changes | Dependencies and review |
|---|---|---|---|
| Coordinator | codex/pc-integration / WSL cm0102-pc | R3 evidence/acceptance; shared Cargo workspace and lockfile, integration, status | Receives workers' exact revision/evidence; independent reviewer required for coordinator implementation |
| Worker A — GPT-6.1 Sol, medium | codex/pc-r1-rng / WSL cm0102-pc-r1 | portable RNG crate, corpus/provenance, native/WASM execution harness, checkpoint | R2 installs pinned toolchain; coordinator owns workspace edits; coordinator reviews fidelity and exact revision |
| Worker B — GPT-6.1 Sol, medium | codex/pc-r2-recovery / WSL cm0102-pc-r2 | toolchain recovery, bounded adapter/supervisor defects and tests, fresh replay receipt | No live original execution; coordinate heavy slot with A; independent exact-revision review |

Routing follows AGENTS.md with bounded implementation workers; stronger review is reserved for subtle numeric/integration findings. Worker prompts use compact explicit inputs rather than full conversation duplication. Model/token usage is recorded only when exposed; coordinator model identity and exact billing totals are not exposed by this interface. Reporting goes to the coordinator and the existing progress document after verification, not a parallel roadmap.

## Accepted increment evidence

[R1](../research/PC_R1_RNG.md), [R2](../research/PC_R2_RECOVERY.md), and [R3](../research/PC_R3_MANAGEMENT.md) retain scoped contracts and receipts. Delivery [PR #32](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/32) records exact-head review, CI and merge disposition. R3 selects a tactical-plan index on a preinitialized null-owner fixture, not an original UI binding or match-plan contents. Conditional private-capture/Windows gates above were not needed and remain unqualified. Independent review used GPT-6 Astra/high; both implementation workers used GPT-6.1 Sol/medium. No exact token/billing totals are exposed.
