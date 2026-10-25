# PC-R3: bounded club tactical-plan selection

Status: bounded command implemented and verified; exact-head delivery tracked in [PR #32](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/32).

## Evidence and choice

Reversal pin `9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345`,
`reports/tactics-boundary-10.md` and its sites/findings describe setter VA
`008967d0`, row resolver `008982b0` and classifiers `00600a50` / `005409b0` in official
specimen SHA-256 `0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86`.
Image base is `00400000`; RVAs are VA minus that base. These are original
instruction addresses, not host pointers. Reversal is MIT (Derek Rivers, 2026).

Lineup assignment is deferred: the R41 tactics view expressly records no
intentional formation/selection changes, and handlers, persistence and engine
effects are unknown. The selected command sets a club's tactical-plan index.
It does not assign players, edit a formation, apply a plan to a match, or
qualify the human-manager registry path. Its documented original caller is
match setup; this implementation exposes the bounded state operation as an
explicit research workflow, not a reproduced original UI handler.

## Supported state and command

The original qualification supplies preinitialized synthetic tactical context,
four dense club IDs, mapping rows with stride `0x91`, and three first-bank plus
two second-bank plan entries. Club owner pointers at `+0xcf` are null; the
classifier falls back to `005409b0`, which compares club IDs against explicit
synthetic global club counts (four ordinary, zero alternate) and returns zero.
The additional dependency was discovered during actual instruction admission;
it is executed, not stubbed. Option is fixed to zero;
the resolver returns the club ID. No callee is replaced with a stub. Plan
banks themselves are not read by the setter and their content is outside scope.

Rust admits exactly the four-club, five-plan fictional fixture with stable
dense IDs and a structurally validated fictional squad. A plan is an index/name,
not a claim about the 6371-byte original plan contents. Each club references
one plan. Player IDs are unique, club references valid, names bounded, and
the fixture/data identity is fixed. The browser receives a projection only.

`SelectPlan` carries session ID, command ID, expected revision, club ID and
signed plan ID. Valid indices are `0..plan_count`. Preconditions are checked
before mutation. The accepted command writes one selection and emits one
ordered `PlanSelected` event (including old/new indices). Setting the current
plan remains an accepted write. Events and revisions belong to the new Rust
protocol and are not original engine observations. The original write is
the mapping word; no RNG is consumed in the qualified path.

Negative plan IDs and missing/out-of-range clubs, stale revision, wrong
session, reused command ID with changed payload, unsupported schema/profile,
bad references and corrupt saves reject without state mutation. Invalid
original plan IDs enter diagnostics and mutate a diagnostic global; the
Rust host rejects them before invoking the supported transition. Original
diagnostics are explicitly outside the equivalent domain.

Identical command retries return the recorded result, including after
save/reload. Commands execute serially. A small versioned JSON slice save
records profile, fixture identity, full state, deduplication records, ordered
events, payload length and SHA-256. Loading validates everything before
replacing the current state. This is not an original saved-game format.

## Acceptance corpus and unresolved boundaries

Generate an oracle directly from hash-verified PE32 original instructions,
checking admission at every instruction, ABI return/stack, ordered non-stack
writes, unchanged sentinel bytes and classifier/resolver guards. Retain
synthetic input/output data and instruction-range hashes only, never code or
original data. Cover all four rows and five plan IDs, repeated selection,
sequential changes and low-word handling in the original ABI. Rust's narrower
typed input intentionally rejects out-of-domain integers instead of silently
truncating them.

Run the same accepted and rejected command corpus natively and in an actual
browser WASM worker. Compare canonical full state, events and replay results;
save/reload mid-stream must preserve continuation. Browser interaction must
display the validated fictional squad, change the selected plan through Rust,
and preserve the previous state after invalid input/import. Unsupported
commands stay unavailable. Test deliberate wrong row, wrong selection width,
additional write and omitted write against the original corpus.

No dependency on PC-R1 is asserted: the admitted setter/resolver/classifier
path has no RNG. Full owner registry/classification, original UI bindings,
actual tactical-plan contents, original squad capture, match application,
diagnostics, allocation and original saves remain unresolved. No live
Windows observation is required or authorized for this bounded experiment.

## Verified results

The [original instruction oracle](evidence/plan-selection-oracle-v1.json) ran 24
cases across 96 instruction starts without replaced callees. Every call made
one ordered two-byte mapping write and preserved context/club/mapping sentinel
bytes, with the expected return/stack behavior. Each of four deliberately wrong
write models is detected in all 24 cases. The claim is the bounded mapping
transition, not complete hidden-state/register equivalence.

The [browser receipt](evidence/pc-r3-browser-2026-10-25.json) records 37 operations
executed both natively and in a real Chromium 148 WASM worker. Canonical full
state/events/rejections/save outputs match SHA-256
`4f5280e535551f4bc16a05d8b08544c46cb4075d59caf31343397df7754fe873`.
Actual React Apply, Export, Import and corrupt-import rejection passed. Saved
state preserves deduplication and deterministic continuation. The browser uses
Node 22.22.2 for its test host; two missing Chromium runtime libraries
(libnspr4/libnss3) were installed without changing game or Rust pins.

Independent GPT-6 Astra/high review found and verified fixes for initial WASM
buffer allocation detaching a host view, and a public Rust world-construction
bypass. World fields are private, public deserialization is unavailable, and
loading has a private decode type plus full replay validation. The direct
mutation compile-fail check, all Rust behavioral tests, strict TypeScript
checking and builds pass. R1/R2 remain separate crates/host modules; no second
production rules implementation was introduced.


## Subsequent real club/manager extension

[Manager-bound qualification](MANAGER_BOUND_PLAN.md) and
[private-input recovery](PC_R3_CAPTURE_INPUT.md) extend this original increment.
The field at `club+0xcf` is a manager staff pointer; the earlier word "owner"
was a hypothesis. The legacy profile string keeps its old spelling for save
compatibility. The new profile admits three reviewed nonhuman-manager ordinary
clubs from retained Bosman state and implements bank/index resolution through
Rust. It does not qualify human management or original UI handlers. See
[PR #33](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/33).
