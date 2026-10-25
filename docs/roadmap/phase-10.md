# P10 — Extensible game and sustained development

Status: whole-game scope and exit contract; not fully closed. Use the [active PC plan](PC_FIRST.md) for current ordering and [progress](../status/PROGRESS.md) for demonstrated work. Scoped numeric work may proceed before full P02/P04 closure; no phase gate is waived.

## Purpose

Add features without eroding the preserved game.
## Dependencies

P09
## Delivery sequence

1. Promote versioned rules/data extension APIs exercised during earlier slices; start with declarative data packs before arbitrary plugin code.
2. Deliver one substantial optional game feature plus UI, migration, AI interaction and laboratory coverage.
3. Automate extension compatibility matrix, long-term save migration, release profiles and continued research of lower-priority gaps.

## Falsifiable exit gate

One agreed feature changes its intended workflow in an extended profile, survives save/reload, and the full faithful regression corpus remains unchanged with that feature disabled.
## Authority and contracts

Feature set/version is persisted; missing/incompatible extensions fail clearly. Removing an extension requires a defined migration or rejection.

Use the simulator manifest, backend capability, evidence and command contracts. Exact acceptance cases and measured resource budgets are frozen before implementation of this phase. See [simulator](../architecture/SIMULATOR.md) and [fidelity contract](../architecture/EVIDENCE_AND_FIDELITY.md).
## Concurrency and stale state

Independent evidence gathering may run concurrently within resource limits. Claims carry source/evidence revisions; a changed build or scenario invalidates the corresponding cached result. Simulation jobs use fenced attempts. Integrated game mutation remains ordered. A phase closes only against one recorded integration revision.
## Parallel lanes and convergence

Read-only inventory, scenario authoring and interface design may overlap once shared contracts exist. Gate evidence and integration reviews converge before the next dependent phase closes.
## Non-goals

No unrestricted native plugin execution or network-required AI gameplay by default.
## Closure record

Record completed scope, exact revisions, executable evidence, remaining unknowns, accepted deviations, benchmark results and carry-forwards. A missed gate stays open; do not rename partial delivery as completion.

## Additional delivery acceptance

Provide a validated data/rules editing and import workflow for the first extension, with referential-integrity checks, migration preview and clear handling of missing extensions.
