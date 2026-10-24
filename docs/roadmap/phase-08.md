# P08 — Complete playable application

Status: planned; implementation and gate evidence remain outstanding.

## Purpose

Deliver the whole player experience and supported play modes.
## Dependencies

P07
## Delivery sequence

1. Complete new-game setup, manager workflows, news/inbox, tables, staff/player/club screens, settings and navigation inventory.
2. Integrate data/asset import, original-style presentation, localisation, keyboard/accessibility and save management.
3. Complete verified supported multi-manager/network paths or surface a programme scope decision; human acceptance against recorded original journeys.

## Falsifiable exit gate

A player can create a career, manage a season, interact with matches and management decisions, save, reload and continue through the browser with every baseline workflow accounted for and no mandatory placeholder screen.
## Authority and contracts

Rust validates all commands; browser projections carry revision IDs. Network paths, if in baseline, have separate authority/reconnect contracts.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

Read-only inventory, scenario authoring and interface design may overlap once shared contracts exist. Gate evidence and integration reviews converge before the next dependent phase closes.
## Non-goals

No generic modern UI substituted for CM behaviour without explicit feature-profile decision; visual polish does not excuse missing rules.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.

## Additional delivery acceptance

Complete storage-quota handling, atomic save replacement, export/import, browser refresh/crash recovery, asset/font/localisation loading and player-visible progress. Confirm these against the expanded coverage register.
