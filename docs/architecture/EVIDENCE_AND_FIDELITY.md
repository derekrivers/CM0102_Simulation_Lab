# Evidence, mapping and fidelity contract

## What 'entire game mapped' means

Every in-scope original function, global, record type, file format, event boundary and player workflow has an inventory entry. Each is either understood and linked to implementation/tests, classified as platform/runtime replacement with justification, or explicitly unresolved. Reachable unknowns cannot disappear from the denominator. 'All functions named' is a useful index but not whole-game understanding.

Inventory layers: binary/address map; data layouts and ownership; call/field/event relationships; subsystem behaviour contracts; player workflow/state-machine map; reconstruction links and validation results. Track platform/runtime items separately without silently excluding ambiguous game code.

Function identity is `(executable_sha256, RVA)` plus recorded image base, size and aliases. Globals use the same version-scoped address identity; object fields include owner type/offset/width and confidence. File offsets are converted using PE section mappings, never a universal add-0x400000 shortcut. Rust functions may implement multiple original routines, and one original routine may map to several modules: relations are many-to-many.

## Records and promotion

A function claim includes: proposed purpose; calling convention; inputs/outputs; preconditions; read/write sets; called functions; RNG use; numeric/rounding rules; lifetime/ownership; relevant player action; exact code address ranges; supporting and contradicting observations; tests; provenance; reviewer; confidence and residual gaps. Import upstream names unchanged as aliases with upstream confidence, not our acceptance.

Keep independent dimensions: `inventory_status`, `execution_coverage`, `semantic_status`, `implementation_status`, `validation_scope`. Semantic progression: imported hypothesis -> investigated -> experiment-supported -> reviewed contract; any stage can become disputed. Implementation progression: absent -> partial -> implemented -> validated for named corpus. Never treat this as universal mathematical proof.

A reviewed behaviour requires code inspection plus discriminating evidence where executable, a recorded alternative explanation, boundary/negative cases, and a reproducer. Static-only unreachable/runtime findings may be reviewed with an explicitly narrower evidence class. The evidence index stores candidates separately from accepted contracts and preserves all revisions.

## Fidelity levels and release labels

| Level | Required evidence | What it does not prove |
|---|---|---|
| F0 Inventory | Version-scoped addresses/types/workflows registered | Behaviour |
| F1 Observed | Scenario reaches path; inputs/outputs retained | Causality or completeness |
| F2 Local equivalence | Targeted routine/state parity against original, boundary cases | Whole career parity |
| F3 Journey equivalence | Ordered subsystem events and semantic snapshots agree for named scenarios | All settings or all seasons |
| F4 Integrated fidelity | Whole-game matrix, save/reload, seasons and player workflows meet declared criteria | Exact every-seed equivalence if not demonstrated |

Report the strongest achieved level per subsystem/profile, with corpus version and exclusions. The target is F4 across the declared original game scope, with exact local/journey comparisons wherever feasible. Distributional results have their own label and cannot be promoted to exact parity.

## The compatibility risk to resolve early

Upstream testing documents memory-layout-sensitive outcomes. Investigate whether observed changes arise from RNG seeding/consumption, pointer-based ordering, uninitialised bytes, allocator behaviour or another mechanism. Record a minimal cause for each confirmed class. Options are controlled original-layout replay for reference runs, semantic-state comparisons, or a narrow Rust virtual-address/allocator compatibility layer. Do not scatter fake pointers through domain APIs prematurely.

Original crashes/undefined behaviour may not have one portable answer. Capture the actual baseline environment; record safe deviations when a faithful reproduction would be unstable. A claim of 'bit-identical complete careers' is withheld until demonstrated. If clean domain modelling and strict original-layout behaviour conflict, record the tradeoff and its user-facing compatibility consequences before changing the target.

## Comparator hierarchy

1. Raw bytes: deterministic buffers and sections where meaningful; retain hashes and raw artifacts.
2. Structured exact values: stable entity IDs, field widths, money/dates, events, RNG state/count and scheduler order.
3. Policy-defined canonical values: exclude only proven nonsemantic padding, address relocation or UI metadata at exact schema paths. Cross-reference raw fields; unmapped bytes remain visible.
4. Numeric equivalence: only where evidence justifies an explicit per-field error model; a changed branch outcome always matters.
5. Statistical profiles: named populations, fixed experiment plan, uncertainty and holdout validation.

Save byte equality is valuable but not always cross-backend meaningful. Maintain a versioned semantic decoder and independent raw retention. Never compare only a selected subset and call the whole state equal. Report compared fields, unparsed bytes and unobserved behaviour separately. Stable-ID alignment must itself be verified.

## Acceptance matrix

Baseline axes: supported languages, nations/leagues/database sizes, manager counts and supported play modes, UI actions, active/holiday AI, detailed/quick matches, start/load/resume, season boundaries, domestic/international calendars, transfer windows, long careers and host target. Inventory actual original options before finalising this matrix.

Preserve the original supported hot-seat/network/multiplayer paths in the scope inventory if present; verify what exists rather than assuming a single-manager game is complete. Network modes can be later milestones but require a visible release gate or explicit scope decision.

Use pairwise coverage for broad combinations plus targeted high-risk combinations, all special competition formats and edge states. Maintain an external holdout corpus not used to tune implementations. Human acceptance checks pace, information visibility, navigation, wording, sorting and the familiar management loop as well as screenshot similarity.

## Rust slice definition of done

A slice has original references, documented contract and field widths, explicit RNG/clock access, positive/boundary/negative tests, a reproducible original/Bosman/Rust comparison with authority labels, save/reload evidence where stateful, native/WASM result parity, readable implementation, and known gaps. No slice is accepted only because it 'looks like football'.

## Example overnight experiment

Hypothesis: a particular renewal decision depends on player age and contract duration. Start from a validated pre-negotiation snapshot; change one valid input through a controlled adapter; preserve all other fields and RNG state. Run a boundary matrix around relevant ages/durations, record called functions and contract/finance writes, and compare original versus Bosman. A hit correlation identifies candidates; callsite/value tracing and a counterexample test distinguish the candidate formula. Port the supported rule to Rust and rerun the original-function and journey corpus. This is a proposed experiment, not a discovered CM formula.

## Implementation contracts

Use [reconstruction method](RECONSTRUCTION_METHOD.md), [runtime contracts](RUNTIME_CONTRACTS.md), [verification plan](../research/VERIFICATION_PLAN.md) and the [bootstrap checkpoints](../roadmap/BOOTSTRAP.md) to turn these decisions into bounded executable work.
