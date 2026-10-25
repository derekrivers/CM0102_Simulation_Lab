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

## Executed bounded result

Exact source `89c0c52` passed fresh native/release-WASM builds and strict
TypeScript/build. The new journey helper passed all seven cases (four route
controls plus synthetic/retained/fresh) in 18.46 seconds, including real persistent
process close/reopen and native continuation. Fresh WASM is exactly the delivered
R7 `50c8d50d4a24869e6fc9980c357ef5cef113c3ccbbab0c21a7e3829dd511a0ee`.

The unchanged full browser suite passed 552 operations in 14.61 seconds and the
unchanged storage suite passed twelve profiles in 23.76 seconds, including both
invalid-head cases. Both complete parsed receipt objects exactly equal the
previous R7 receipts: all 552 operations/twelve profile objects and earlier
375/nine subsets remain unchanged. No canonical expected result was rewritten.
[Journey receipt](evidence/pc-r10-browser-journey-v1.json) and
[validation seals](evidence/pc-r10-browser-validation-v1.json) retain exact
source/artifacts, commands, times and private log identities. Build times were
not individually measured. Two shell CRLF transport failures occurred before
runner execution; they are retained and do not count as executed acceptance
failures. No acceptance runner failed. The independent-review correction below supersedes the initial helper import proof; product source required no correction.

Independent exact-head review and delivery disposition are separate gates. The
real squad/lineup milestone remains incomplete; future input/action/admission
gates above remain required.

### Independent-review correction

C identified a vacuous wait in the new helper: its exported revision-2 import
could match the already visible revision-2 status before asynchronous load. The
initial v1 receipt remains retained and is insufficient proof of that import.
Exact helper source `e8436b1` now changes and verifies memory at revision 3 before
importing revision 2, then waits for revision 2 and compares the complete state.
The affected helper passed all seven cases again in 15.37 command seconds
(14.514 helper seconds), including synthetic/retained/fresh real process reopen
and now discriminating export/import restoration. UI/preview/native/WASM/artifacts
are unchanged, so prior complete 552-operation/twelve-profile acceptance remains
applicable. No canonical expected result was changed.

[Corrected journey receipt](evidence/pc-r10-browser-journey-v2.json) and
[correction seals](evidence/pc-r10-browser-validation-v2.json) bind the exact
source/log/artifacts and preserve the review finding. Independent final approval
remains separate from this implementer's record.
