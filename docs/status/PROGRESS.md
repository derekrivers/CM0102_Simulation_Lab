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

## Remaining engineering

1. The real ordinary-club/nonhuman-manager path is now qualified. Next investigate the reserved human-manager registry path and its lifecycle before exposing human-manager controls or claiming original UI/match effects.
2. Original Windows startup, clean-data consumption, A/A and original/Bosman comparisons remain separate medium-helper gates. No original process was launched; this increment reused a retained private capture.
3. Actual-game RNG table qualification, full initialization/seeding, x87 large bounds, original saves and complete match behavior remain open.
4. Storage-failure recovery, cgroup/lease/resource fencing, durable orchestration and unattended campaigns remain unqualified.
5. Dormant launcher retirement requires a separately reviewed policy transition; frozen controls were not weakened.

These three accepted bounded increments do not complete the simulator, P02/P04 whole-phase gates or unattended-operation qualification.

## Repository reset

This change removes duplicate bootstrap/implementation plans and the superseded planning review from the current tree, records their Git history, and makes one PC plan authoritative. It corrects the stale Explorer-token-duplication instruction, separates demonstrated results from plans, and adds the pinned Reversal reproduction receipt. Existing Rust/C#/Python source, input locks, private data and frozen CI/launcher contracts are preserved.

Cleanup verification, independent review and merge disposition are tracked in [PR #31](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/31), based on `196d064a0bd8e9ecc152595f8bb438d879b159bc`. The PR records the exact reviewed head, CI runs and final merge identity. Local documentation checks resolved all 155 relative links and verified the receipt against the pinned Reversal artifact hashes; existing source/config/workflows have no diff. A passing cleanup does not mean the runner gaps are fixed, the local Rust toolchain is installed, or implementation has restarted. No whole-game phase is closed by this reset.
