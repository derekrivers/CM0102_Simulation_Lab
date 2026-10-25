# P07 — Competitions and complete world lifecycle

Status: whole-game scope and exit contract; not fully closed. Use the [active PC plan](PC_FIRST.md) for current ordering and [progress](../status/PROGRESS.md) for demonstrated work. Scoped numeric work may proceed before full P02/P04 closure; no phase gate is waived.

## Purpose

Make full seasons and careers coherent across all original supported competitions.
## Dependencies

P05, P06
## Delivery sequence

1. Port competition-specific formats, draws, fixtures, tables, tie-breakers, promotion/relegation, qualification and prize allocation.
2. Integrate internationals, scheduling conflicts, AI world decisions, records, retirements/regeneration and season rollover.
3. Build all-supported-league coverage matrix and targeted rare-calendar/format cases; run quick and detailed lifecycle campaigns with save/load.

## Falsifiable exit gate

A representative multi-nation career crosses two complete season rollovers, domestic and international tournament boundaries, preserves financial/player/history consistency and meets its declared original-reference comparisons; every remaining league-specific gap is enumerated.
## Authority and contracts

Calendar/event ordering is authoritative and versioned. No automatic rule modernisation in faithful mode.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

Read-only inventory, scenario authoring and interface design may overlap once shared contracts exist. Gate evidence and integration reviews converge before the next dependent phase closes.
## Non-goals

Representative careers do not certify every league; full matrix closure continues into P9.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.
