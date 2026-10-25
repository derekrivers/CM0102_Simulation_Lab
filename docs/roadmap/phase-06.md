# P06 — Detailed and quick match reconstruction

Status: whole-game scope and exit contract; not fully closed. Use the [active PC plan](PC_FIRST.md) for current ordering and [progress](../status/PROGRESS.md) for demonstrated work. Scoped numeric work may proceed before full P02/P04 closure; no phase gate is waived.

## Purpose

Reconstruct both match paths and their management/world effects.
## Dependencies

P04
## Delivery sequence

1. Map/port tactical selection, match state progression, player actions, substitutions, officials, injuries and discipline.
2. Port quick-result path independently and model selection policy; connect commentary/statistics/ratings and post-match state updates.
3. Use first-divergence traces and controlled RNG, targeted branch cases and independent distributional holdouts; add playable match interaction.

## Falsifiable exit gate

The declared detailed/quick corpus covers normal time, draws, extra time/penalties where applicable, substitutions, cards and injury paths, with verified event/state comparisons and correct post-match integration.
## Authority and contracts

Match contexts own temporary state; final writes commit in stable order. Parallel matches are deferred until ordering/RNG equivalence is proved.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

After P04, P05 management and P06 matches can proceed in parallel; both converge at P07. UI workflows accompany each slice.
## Non-goals

Score distributions alone cannot close this phase; unrelated management domain ports may proceed concurrently.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.
