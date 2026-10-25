# P01 — Reliable headless laboratory

Status: whole-game scope and exit contract; not fully closed. Use the [active PC plan](PC_FIRST.md) for current ordering and [progress](../status/PROGRESS.md) for demonstrated work. Scoped numeric work may proceed before full P02/P04 closure; no phase gate is waived.

## Purpose

Run bounded experiments unattended and keep every result reproducible.
## Dependencies

P00
## Delivery sequence

1. Implement Rust manifest validator, CLI and Bosman process adapter; sanitise environment and isolate writable paths.
2. Add PostgreSQL queue, fenced leases, attempt/artifact store, cancellation, bounded retries and progress watchdogs.
3. Adapt full-play/quick-result runners; add first-match and 30-day scenarios; measure CPU/RAM/disk and failure drills.

## Falsifiable exit gate

A 24-hour single-worker pilot accounts for every attempt with no silent result loss, reaches intended successful endpoints for startup/load, short world-advance and targeted match scenarios, survives an injected worker restart, and reproduces a selected result from its manifest. Correctly classified failures alone cannot satisfy this gate.
## Authority and contracts

Scheduler may execute only approved templates and pinned binaries. No public API or worker write access to source control.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

Read-only inventory, scenario authoring and interface design may overlap once shared contracts exist. Gate evidence and integration reviews converge before the next dependent phase closes.
## Non-goals

No autonomous semantic promotion, throughput promise or inference dependency.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.

## Upstream acceptance

Use [Bosman Edition](https://github.com/maxevans60/cm0102-bosman-edition) at the pinned source revision. Record actual build and upstream test results. Demonstrate distinct full-play and quick-result jobs; prove expected paths for sampled fixtures, isolate configuration and remove machine-specific scheduling assumptions. The initial adapter may drive the internal UI without a visible display; it is not yet a pure game-engine API.
