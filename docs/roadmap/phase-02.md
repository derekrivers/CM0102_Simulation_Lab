# P02 — Calibrated references and replay

Status: whole-game scope and exit contract; not fully closed. Use the [active PC plan](PC_FIRST.md) for current ordering and [progress](../status/PROGRESS.md) for demonstrated work. Scoped numeric work may proceed before full P02/P04 closure; no phase gate is waived.

## Purpose

Establish what each backend can actually prove.
## Dependencies

P00
## Delivery sequence

1. Run A/A replay corpus on original and Bosman; capture RNG/state/clock/layout constraints and test instrumentation neutrality.
2. Add original-function adapter and selected RNG/numeric/date cases; compare original/Bosman state and first divergences.
3. Build raw/semantic comparator with reviewed masks and negative controls; qualify the local calibration corpus. Supply that corpus to the separate continuous-operation gate in P03.

## Falsifiable exit gate

Ten representative micro/journey scenarios each pass ten A/A repeats at their declared level, injected mismatches are detected, and every original/Bosman discrepancy is classified without weakening the comparator.
## Authority and contracts

Comparator changes require review; unresolved layout/numeric issues block exact-parity claims for affected slices, not unrelated research.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

Read-only inventory, scenario authoring and interface design may overlap once shared contracts exist. Gate evidence and integration reviews converge before the next dependent phase closes.
## Non-goals

No claim that ten scenarios cover all game behaviour or that seed equality proves replay.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.
