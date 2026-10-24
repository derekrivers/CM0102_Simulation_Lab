# P09 — Whole-game fidelity and compatibility release

Status: planned; implementation and gate evidence remain outstanding.

## Purpose

Close the original scope and make compatibility claims defensible.
## Dependencies

P08
## Delivery sequence

1. Complete the whole-game matrix across leagues, languages, supported modes, long careers and special rules; adjudicate every release-blocking unknown.
2. Finish original database/asset import and original-save import across declared supported variants; certify new saves/migrations and malformed-input handling.
3. Run held-out native/WASM/regression/soak corpora, performance budgets and human acceptance; publish fidelity and deviation report.

## Falsifiable exit gate

Every baseline feature has a passing acceptance record or an explicitly accepted documented deviation; no unresolved release-blocking reachable behaviour, supported save corpus passes, and an independent tester can reproduce the release report.
## Authority and contracts

Release identity freezes core/profile/schema/input definitions. Compatibility regressions block the faithful release.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

Read-only inventory, scenario authoring and interface design may overlap once shared contracts exist. Gate evidence and integration reviews converge before the next dependent phase closes.
## Non-goals

Original-save export is not promised without a separate requirement; no universal every-seed parity claim beyond demonstrated evidence.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.

## Scope closure rule

Every confirmed baseline feature row in [COVERAGE_REGISTER.md](../research/COVERAGE_REGISTER.md) must resolve to its acceptance scenarios and result revision. Expand competition rows into each supported format/nation, and UI rows into actual screens/actions during P00. Representative seasons alone cannot close this gate. Any proposed exclusion is a visible scope decision, not a passing test.
