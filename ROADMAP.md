# Roadmap

Updated 25 October 2026. **The first bounded Rust RNG and stateful browser workflow now pass their scoped acceptance checks.** The full objective remains a faithful, playable and extensible reconstruction of the entire game.

## Current delivery sequence

| Target | Status | Acceptance |
|---|---|---|
| PC-R0: recover research evidence | Complete for the selected input | Reversal checks passed; fresh official-instruction RNG outputs match retained hashes |
| PC-R1: CRT and small-bound RNG | Verified | 1,024 CRT steps + 2,570 bounded calls; all exposed state matches; native and actual WASM execution; checkpoint continuation |
| PC-R2: lab/reference recovery | Targeted recovery verified; wider qualification open | Working WSL toolchain, fresh bounded Bosman replay, scoped evidence ledger and necessary Windows qualification |
| PC-R3: stateful management workflow | Bounded tactical-plan selection verified | An evidenced Rust command with rejection cases, browser interaction, native/browser equality and save/reload |
| PC-R4: human tactical registry | Bounded delivery merged in PR #35 | Real reciprocal binding, connected original instructions, ordered selection-byte effect, native/browser equality and explicit v3 continuation |
| PC-R5: fresh pinned capture | Bounded delivery merged in PR #36 | Sealed current-platform derivative, exact repeated capture and endpoint saves; actual data-open consumption remains unknown |
| PC-R6: durable browser recovery | Existing-profile delivery merged in PR #34; human v3 integration verified | Exact Rust saves in IndexedDB, atomic replacement/fallback, failure reporting and session/tab fencing |

The [active PC delivery contract](docs/roadmap/PC_FIRST.md) contains the task checklists, dependencies, exclusions and stop conditions. [Progress](docs/status/PROGRESS.md) records results. [Reversal integration](docs/research/REVERSAL.md) pins the reusable research and distinguishes official instruction emulation from a different GDI specimen's live evidence.

Use Windows for the reviewed reference route, WSL for Linux lab/build work, and a portable Rust core for native/WASM behaviour. Numerical work can start from adequate local original-instruction evidence without completing all P02 calibration. This scoped exception does not close formal P02/P04 gates or authorize live execution.

## Whole-game scope retained

These contracts describe programme scope and eventual exit gates. Their phase numbers are not today's ordered task queue, and none is claimed fully closed.

| Phase | Scope | Current position |
|---|---|---|
| [P00](docs/roadmap/phase-00.md) | Baseline, inputs and scope | Substantial inventory/input work demonstrated; remaining scope/gate review open |
| [P01](docs/roadmap/phase-01.md) | Reliable headless laboratory | Bounded local execution demonstrated; durable service deferred |
| [P02](docs/roadmap/phase-02.md) | Calibrated references and replay | Synthetic comparator and scoped original-instruction evidence; original-process calibration open |
| [P03](docs/roadmap/phase-03.md) | Continuous evidence and mapping | Deferred continuous campaigns; targeted research continues |
| [P04](docs/roadmap/phase-04.md) | Rust foundation and browser slice | Begins with PC-R1; PC-R3 provides the first player workflow |
| [P05](docs/roadmap/phase-05.md) | People and club management | Later |
| [P06](docs/roadmap/phase-06.md) | Detailed and quick matches | Later, alongside P05 after relevant foundation |
| [P07](docs/roadmap/phase-07.md) | Competitions and world lifecycle | After P05/P06 |
| [P08](docs/roadmap/phase-08.md) | Complete playable application | After world integration |
| [P09](docs/roadmap/phase-09.md) | Whole-game fidelity and compatibility | After playable scope and full evidence |
| [P10](docs/roadmap/phase-10.md) | Deliberate extensions | After faithful baseline; compatibility interfaces planned earlier |

Scope includes setup, databases/assets, players/staff, contracts/transfers, finances, training, matches, competition rules, news, saves, navigation and supported play modes. Rust owns all game rules. A match runner, function atlas or static UI is not completion.

## Deferred work and re-evaluation

VPS capacity purchases, 24/72-hour campaigns, distributed workers, PostgreSQL deployment, dashboards and Jev trials are not immediate dependencies. Retained designs are reference material, not instructions to implement them now. Existing dormant Windows launcher retirement needs a separate reviewed verification-policy transition; do not bypass its guards.

After two focused setup sessions without useful execution, diagnose and reassess before expanding infrastructure. Replan a feature when original evidence contradicts its contract, state cannot replay, or unresolved dependencies overwhelm its boundary. Measure accepted behaviours and demonstrated workflows, not mapped-function or PR counts. Estimate broader delivery after several completed slices.

[Non-negotiables](docs/NON_NEGOTIABLES.md), [delivery rules](docs/runbooks/delivery.md) and the [historical index](docs/history/README.md) preserve fidelity, provenance and the earlier decisions.
