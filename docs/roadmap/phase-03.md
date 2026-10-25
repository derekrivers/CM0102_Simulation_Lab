# P03 — Continuous evidence and function mapping

Status: whole-game scope and exit contract; not fully closed. Use the [active PC plan](PC_FIRST.md) for current ordering and [progress](../status/PROGRESS.md) for demonstrated work. Scoped numeric work may proceed before full P02/P04 closure; no phase gate is waived.

## Purpose

Turn continuous runs into an inspectable behavioural map.
## Dependencies

P01, P02
## Delivery sequence

1. Enrich the function/global inventory imported in P00; add measured execution/semantic/implementation coverage dimensions without overwriting upstream assertions.
2. Add address-correlated coverage, targeted traces, scenario prioritisation, failure reduction and claim review UI.
3. Pilot Jev in shadow mode with held-out triage evaluation; keep deterministic scheduling fallback; optional reasoning worker drafts contracts.

## Falsifiable exit gate

For 20 triaged functions across at least four whole-game domains, deliver at least five reviewed experiment-supported contracts across at least two domains with original-backed evidence at their stated level. Demonstrate rejection of a known unsupported claim and a replayable failure bundle. Complete the separate 72-hour continuous-operation qualification. Optional Jev evaluation is not required to close these core gates.
## Authority and contracts

Models produce candidate claims/routing only. Reviewers own acceptance; all updates use evidence revision checks.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

Read-only inventory, scenario authoring and interface design may overlap once shared contracts exist. Gate evidence and integration reviews converge before the next dependent phase closes.
## Non-goals

No automatic rename-as-proof or implied mapping completion; Jev adoption is conditional on evaluation.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.

## Existing map as the starting point

Use [cm0102-function-map](https://github.com/maxevans60/cm0102-function-map) aliases and provenance when correlating Bosman traces and original addresses. Keep imported confidence, local evidence, review and Rust implementation status separate. Repeated ingestion must be idempotent and an upstream update must not erase local findings.
