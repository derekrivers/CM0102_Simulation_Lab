# R10 browser management journey

Status: existing qualified v5 setup convenience; real squad/lineup milestone remains gated.

## Existing journey and frozen boundary

The default v1 view displays a fictional squad. Ordinary captured v2 profiles
admit club/manager context but contain no squad records. Human v3/v4/v5 profiles
admit initialized bindings and the already qualified registry operations, with
no squad membership, player names, positions or lineup assignments. V5 exposes
explicit tactical lookup and labels the last result with its historical revision.
Rendering and control selection do not invoke the operation.

The current coherent supported journey is: explicitly load a locally configured
independently admitted connected human reference; inspect its origin/boundary;
explicitly run supported research commands; save in this browser or export;
close/reopen; continue with Rust state/history/deduplication. This is useful setup
for the existing tactical workflow and does not complete the requested real
squad/lineup milestone. An empty mapping is never presented as a squad.

A future squad screen must consume only independently admitted Rust-owned IDs,
evidenced membership/link relationships and supported command/result fields.
Names, positions, ratings and football eligibility cannot be inferred from
unqualified record labels. A/B original-state/action qualification, C projection
admission and lead Rust/save compatibility review precede that integration. No
new projection, action, save/profile or automatic migration is introduced here.

## Local fixture transport

`EFFECTIVE_REFERENCE_FIXTURE` configures one literal loopback preview route,
`/effective-reference-fixture.json`. The preview accepts no client-selected path,
requires an absolute configured path and a file of at most 65,536 bytes, sends
`Cache-Control: no-store`, and exposes no directory listing. Missing/unreadable,
relative or oversized configured files receive 404. Private fixtures are served
on explicit request, never copied to dist or Git. Like the existing ordinary and
human fixture routes, this preview is intended for a trusted local browser.
The route is availability only: Rust still validates the exact complete fixture
and rejects unsupported identities atomically. The client does no admission.

The new button exists on both ordinary and human views, reducing manual fixture
handling. Missing-route/fetch failures say the current state is unchanged;
Rust rejection uses the existing invalid-state message. The human screen
explicitly states that qualified squad records and lineup changes are unavailable.
Synthetic and captured origin labels stay distinct. The optional
`MANAGEMENT_PREVIEW_PORT` (default 8766, 0 for an OS-selected port) supports isolated
acceptance without sharing a listener; binding remains 127.0.0.1.

## Acceptance frozen before execution

New standalone `apps/management/check-browser-journey.cjs` adds no canonical
expected results and edits no existing acceptance helpers. It uses the actual
preview, native management-corpus and Chromium WASM worker:

- Missing route, relative path and an unsupported served fixture preserve the
  complete active Rust world; unlisted/path-query routes reject.
- Explicit local setup admits each configured retained/fresh v5 fixture and the
  clearly labeled synthetic control, matching complete native state.
- Control selection stays pure; explicit UI lookup matches native complete
  response/state/ordered events and exact save bytes.
- A real persistent Chromium process closes/reopens, recovers exact state and
  continues a supported command with complete native equality; historical lookup
  remains historical. Export/import bytes and continuation remain exact.
- Existing 552-operation and twelve-profile scripts run unchanged, including
  malformed head, both-invalid checkpoints, corrupt fallback, actual abort,
  accepted-but-unsaved visibility and delayed/stale same-profile fencing. Their
  canonical results must equal the delivered R7 receipts, not be regenerated.

No Rust source changes means new storage semantics are not claimed. Original
process/file-use, original saved games, real squad, lineup assignment, plan
contents and match effects remain unqualified. Executed results and exact source/
artifact identities are recorded separately after validation.
