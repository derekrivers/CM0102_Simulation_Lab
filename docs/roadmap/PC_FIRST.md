# Active delivery plan: PC-first reconstruction

Decision: 25 October 2026. The owner accepted the PC review and Reversal reuse recommendations. This replaces the opening implementation sequence and bootstrap planning. It does not close any whole-game phase gate or authorize live Windows execution.

## Outcome and ordering

Build one original-instruction-backed Rust RNG slice, execute the same corpus natively and in WASM, and prove checkpoint continuation. Then deliver one bounded stateful management workflow. Simulation Lab remains the implementation repository; [Reversal](../research/REVERSAL.md) is a pinned research source. Rust owns behaviour; React/TypeScript owns presentation.

| Package | Status | Demonstrable target | Dependency |
|---|---|---|---|
| PC-R0: evidence recovery | Complete for the selected RNG input | Retained research checks pass; fresh official-instruction oracle and synthetic table match retained hashes | Receipt in the Reversal evidence record |
| PC-R1: portable RNG | Next implementation | 1,024 CRT steps and 2,570 bounded calls match every exposed result/state field; actual native/WASM equality and checkpoint continuation | PC-R0 and a working pinned toolchain |
| PC-R2: reference and lab recovery | Scoped follow-up; docs reconciliation included in this reset | Fresh bounded Bosman replay; reconciled evidence ledger; qualified Windows observations when needed | Each claim's own source, specimen and execution prerequisites |
| PC-R3: player-visible stateful workflow | Planned | One evidenced management command, invalid-action rejection, native/browser equality, save/reload continuation | Relevant PC-R1/PC-R2 evidence and an accepted command contract |

PC-R1 may proceed before full P02 calibration and the Windows helper campaign. This is a scoped numeric implementation, not formal P02/P04 closure. Original-process and broader journey claims still require their corresponding gates. B0/B1 remain historical checkpoint names; B2 calibration and B3 reconstruction continue through these packages. B4/B5 continuous operations stay deferred.

## PC-R1 acceptance contract

Use the pinned Reversal CRT generator at VA `00946a04` and small-bound branch at VA `0090cfc0`. Addresses identify the original specimen; they are not Rust pointers. Inspect source/disassembly and original-instruction outputs, not TypeScript alone.

Implement one small portable compatibility crate or module. Inject the 51,000-word synthetic table and explicit fixed-width state. Keep filesystem, clock, processes, database and ambient randomness outside the library. The existing Linux lab supervisor is a host adapter and must not become a WASM dependency.

Admitted corpus: sampled signed bounds within -65,535 through 65,535, CRT wrapping arithmetic, zero-bound no-consumption, cursor increment/wrap and CRT offset update. Freeze supported cursor, offset and table-value domains before coding. Invalid states and unsupported inputs must fail without partial mutation. A sampled corpus is not exhaustive proof of the domain.

- [ ] Review the routine contract against the pinned original instructions and oracle; preserve attribution and artifact identities.
- [ ] Match all 1,024 CRT steps and 2,570 bounded calls, including exposed state fields and sequential stream checkpoints.
- [ ] Demonstrate that negative controls detect wrong wrap, extra CRT consumption, zero-bound mutation and wrong arithmetic; reject unsupported bounds, state and table inputs.
- [ ] Execute the same Rust corpus natively and through WASM, comparing canonical output/state hashes. Building WASM alone does not pass.
- [ ] Export/reload a versioned Rust RNG checkpoint including table identity, and demonstrate identical continuation. This is not original saved-game compatibility.
- [ ] Pass formatting, lint, relevant build/behaviour checks and independent review of the exact revision. Retain commands, tools, hashes, scope and review outcome.

Excluded: large-bound x87 branch, OS-time seeding, full initialization, actual-game table qualification, original-save restoration, additional random sources, original-process equivalence and match outcomes. Preserve source/oracle contradictions as failures; do not adjust expected values to suit the port.

## PC-R2 acceptance and outstanding engineering

- [ ] Establish a WSL-native development checkout and pinned toolchain, preserving historical controls and private evidence. Rust/cargo were not found on the checked Windows/default WSL paths during recovery; setup remains to be done.
- [ ] Reproduce the accepted fixed-clock, seed-1, 14-day Bosman replay with fresh artifact identities before using that deployment for new claims. Rehashing old artifacts is not a new replay.
- [ ] Reconcile research by executable hash, RVA and scoped behaviour. Do not add Reversal's 9,241 inferred functions to the map's 11,747 starts as a coverage total.
- [ ] Recover/hash private capture inputs when an experiment needs them; public metadata alone does not reproduce Reversal's live GDI result.
- [ ] Qualify required official Windows observations under the [PC medium-helper contract](../architecture/PC_MEDIUM_HELPER_QUALIFICATION_V1.md). Keep synthetic fixture, original launch, clean-data consumption, A/A and Bosman comparison as distinct gates.

Before broadening adapter execution or starting unattended campaigns, address two identified code gaps with bounded tests: `bosman_adapter.rs` buffers nested output with `wait_with_output()` before applying its limit; early failure paths in `process_contract.rs` can return before a final request/log/replay record is published. These are open work, not fixed by documentation cleanup.

The dormant launcher retirement is a separate maintenance task: identify its frozen source/config/contract and workflow dependencies, propose replacement verification, and use the repository's authorized review/protection process. Do not weaken or bypass the base-branch workflow guard to delete it. This task does not block PC-R1 under existing checks; changes to CI itself need that policy transition.

## PC-R3 acceptance contract

Select one original-evidenced stateful squad command after examining dependencies (lineup assignment only if tractable). Freeze the supported state, effects and rejection cases before implementation. Reuse selected Reversal layouts only where useful.

- [ ] Display a validated supported squad fixture and perform the command through Rust; an invalid action leaves state unchanged.
- [ ] Match native/browser state and ordered events, then save/reload and prove deterministic continuation.
- [ ] Keep unsupported commands unavailable and distinguish fictional demo data from captured reference data.

A read-only profile, static match phases or a navigation mock-up does not complete this target. If the chosen action is too coupled, record the evidence and select another bounded stateful action.

## Resource and progress rules

Windows hosts the separately reviewed operator-launched reference route; WSL hosts Linux builds and research. Use native filesystems for active builds, keep private inputs outside Git and live Windows packages outside OneDrive. Initially allow one heavy build or simulation at a time.

No VPS upgrade/purchase, 24/7 campaign, distributed workers, dashboard project, PostgreSQL deployment or Jev pipeline is scheduled. Reconsider infrastructure only when a demonstrated feature or experiment needs it. After two focused setup sessions without useful execution, record the blocker and reassess a simpler route before adding infrastructure.

Measure accepted behaviour contracts, reproducible cases, unresolved divergences and working workflows. Record engineering/model spend when available. Do not use PR counts, named-function percentages or synthetic UI breadth as game completion. Estimate subsequent work after several measured slices; no whole-game completion date is committed.
