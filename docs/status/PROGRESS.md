# Programme progress

Updated 25 October 2026. Current task queue: [PC delivery plan](../roadmap/PC_FIRST.md). Earlier merges and detailed attempts remain in the [pre-reset Git record](../history/README.md); they are historical evidence, not a requirement to repeat all setup.

## Demonstrated evidence

| Area | What is established | Limit |
|---|---|---|
| B0 inventory | Deterministic importer; 11,747 function starts, 6,863 named rows and 4,428 globals; PE-backed address validation | Names are hypotheses, not verified game semantics |
| Official inputs | Exact official executable and separate 760-file clean set rehashed during PC review | Modified installed folder stays separate; staging does not prove a process consumes clean data |
| B1 Bosman | Pinned native build; 45 upstream tests historically passed; retained fixed-clock, seed-1, 14-day same-save protocol replay | Old artifacts rehashed during recovery; no fresh replay in this reset; no original parity |
| Comparator | Synthetic A/A and deliberate divergences exercise comparison mechanics | No qualified real original/Bosman bundle or parity verdict |
| Windows host | Two complete retained probes accepted as stable; fixture and Stage 2 no-UI builds accepted | Fixture UI/production launchers/original have not run in the Lab's qualified route |
| PC-R0 Reversal recovery | Root retained checks passed; fresh official-instruction RNG oracle and synthetic table byte-match retained files | Scoped synthetic state/table; no full initialization, original game process or save compatibility |
| Rust game/browser | Not implemented | PC-R1 is next, followed by a stateful PC-R3 workflow |

Supporting records: [B0](B0_MAP_IMPORT.md), [input qualification](P00_INPUT_QUALIFICATION.md), [Bosman build/replay](B1_BOSMAN_BUILD.md), [smoke observations](B1_CLEAN_SMOKE.md), [Windows host](P02_ORIGINAL_HOST_QUALIFICATION.md), [Reversal receipt and boundaries](../research/REVERSAL.md).

Historical setup failure: the 3.7 GiB/no-swap VPS could not complete the Bosman build. The PC/WSL build did complete (11m19.72s, peak RSS 7,547,840 KiB). The old VPS sizing constraint is not the current PC's specification. No VPS upgrade or continuous campaign is scheduled.

## Remaining engineering

1. Restore a pinned WSL development toolchain and implement PC-R1. Existing Linux lab code is not a native Windows/WASM core.
2. Fix nested Bosman output buffering and failed-attempt artifact publication before widening adapter scope or unattended work. These are known open source gaps.
3. Re-run the qualified bounded Bosman profile before new backend claims; recover any private Reversal capture needed for a selected experiment.
4. Implement/qualify the separate medium-integrity helper only as required by Windows observations, preserving synthetic, original-startup, clean-data and comparison gates.
5. Select and prove the first stateful management command. Browser rendering without Rust state transition does not complete it.
6. Retire frozen dormant launcher infrastructure only through a reviewed policy transition. Existing CI remains in force.

## Repository reset

This change removes duplicate bootstrap/implementation plans and the superseded planning review from the current tree, records their Git history, and makes one PC plan authoritative. It corrects the stale Explorer-token-duplication instruction, separates demonstrated results from plans, and adds the pinned Reversal reproduction receipt. Existing Rust/C#/Python source, input locks, private data and frozen CI/launcher contracts are preserved.

Cleanup verification, independent review and merge disposition are tracked in [PR #31](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/31), based on `196d064a0bd8e9ecc152595f8bb438d879b159bc`. The PR records the exact reviewed head, CI runs and final merge identity. Local documentation checks resolved all 155 relative links and verified the receipt against the pinned Reversal artifact hashes; existing source/config/workflows have no diff. A passing cleanup does not mean the runner gaps are fixed, the local Rust toolchain is installed, or implementation has restarted. No whole-game phase is closed by this reset.
