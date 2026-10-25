# PC-R3: bounded club tactical-plan selection

Status: command selected; original-instruction qualification precedes implementation.

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
