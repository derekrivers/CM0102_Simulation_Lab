# P00 — Baseline and programme contract

Status: planned; implementation and gate evidence remain outstanding.

## Purpose

Freeze what faithful means and make the inputs reproducible.
## Dependencies

Programme entry; no prior phase.
## Delivery sequence

1. Register original 3.9.68 executable/data/asset hashes and supported feature inventory; audit upstream pins and licences.
2. Import the pinned function/global map and preserve provenance, raw files, counts and confidence; record VPS facts and bootstrap the Rust/TS workspace with version locks and synthetic fixtures.
3. Create profile/deviation registry and original/Bosman capability matrix; write minimal original-observation procedure.

## Falsifiable exit gate

The input/provenance manifest is complete for execution inputs actually supplied, both upstream pins are recorded, the map import is idempotent with reconciled counts, and the scope register includes every top-level game domain. Missing binary inputs remain explicit execution blockers; map-only work may proceed. Runtime startup qualification belongs to P01/P02.
## Authority and contracts

Lister supplies local original inputs and VPS facts; implementer owns reproducibility. No proprietary input enters the public repository.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

Read-only inventory, scenario authoring and interface design may overlap once shared contracts exist. Gate evidence and integration reviews converge before the next dependent phase closes.
## Non-goals

No parity claim, unattended campaign or broad engine port.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.

## Required upstream work

Pin [Bosman Edition](https://github.com/maxevans60/cm0102-bosman-edition) and [function map](https://github.com/maxevans60/cm0102-function-map) independently. Import the map before new naming work. Reconcile file schemas/counts, address categories and duplicate/missing entries; never mark imported rows as locally verified. Follow [UPSTREAM_INTEGRATION.md](../research/UPSTREAM_INTEGRATION.md). Create the initial [coverage register](../research/COVERAGE_REGISTER.md), including known unknowns.
