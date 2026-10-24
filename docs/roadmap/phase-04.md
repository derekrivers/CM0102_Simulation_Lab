# P04 — Rust foundation and browser vertical slice

Status: planned; implementation and gate evidence remain outstanding.

## Purpose

Prove native and browser reconstruction can share one deterministic core.
## Dependencies

P02
## Delivery sequence

1. Implement original-compatible RNG/numerics/calendar, typed entity IDs, basic data decoding and explicit host boundary.
2. Add versioned native save skeleton, command/event protocol and a small snapshot-based management workflow.
3. Build a thin React/TS shell using Rust WASM in a worker; native and browser replay the same commands; benchmark representative state sizes.

## Falsifiable exit gate

A bounded supported fixture loads in native and browser Rust, shows a squad, executes one verified bounded stateful squad command, saves/reloads and produces identical canonical state/event hashes across both targets.
## Authority and contracts

One authoritative world mutator; command sequence/revision rejects stale UI actions. Rust compatibility code owns original semantic quirks.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

After P04, P05 management and P06 matches can proceed in parallel; both converge at P07. UI workflows accompany each slice.
## Non-goals

The bounded slice is not yet a complete new game or season; no duplicated JS rules.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.

## Additional delivery acceptance

Prototype browser checkpoint export/import and measure representative world/snapshot size; prove yielding from the worker and cancellation at safe boundaries.
