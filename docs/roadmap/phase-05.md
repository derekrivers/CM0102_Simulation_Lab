# P05 — People and club management

Status: planned; implementation and gate evidence remain outstanding.

## Purpose

Reconstruct the decisions that make a management game.
## Dependencies

P04
## Delivery sequence

1. Port player/staff attributes, selection, training, development, condition, injuries, morale and relationships through evidence-backed slices.
2. Port contracts, transfers/loans, scouting, wages/budgets, board decisions, jobs and corresponding AI; model news and human responses.
3. Add browser workflows and stateful replay/save tests for each delivered subsystem; discover exact lifecycle dependencies before batching implementation.

## Falsifiable exit gate

A controlled multiweek management corpus covers a contract renewal, transfer/loan, training/development change, injury/recovery, scouting report and board/finance update with original-referenced outcomes and native/WASM save continuity.
## Authority and contracts

Finance and ownership updates are atomic; simultaneous bids/decisions follow recorded simulation order. New rules remain profile-gated.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

After P04, P05 management and P06 matches can proceed in parallel; both converge at P07. UI workflows accompany each slice.
## Non-goals

No claim of season completeness before competition/match integration.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.
