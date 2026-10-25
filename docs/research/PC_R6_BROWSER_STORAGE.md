# PC-R6 browser checkpoint contract

The host stores the exact Rust slice-save string. Rust continues to own admission,
rules, serialization, replay validation, events and command deduplication. This
increment changes neither profile nor v1/v2 slice-save formats. IndexedDB is
origin-local; clearing browser data removes it. Private fixtures stay in that
browser and outside public build output. Manual export/import remains available.

## Frozen host interface

One worker serializes engine requests and storage publication in arrival order.
Ordinary Rust operations remain available without storage for native/WASM corpus
comparison. The view uses the storage-enabled host route: `recover`, `persist`,
and existing Rust operations. Accepted command/load/reset/fixture import triggers
a save. Read-only state/export and rejected operations never publish a checkpoint.
An accepted in-memory result remains accepted if storage fails, accompanied by a
separate failure and the last confirmed committed identity. The UI displays both.

Database `cm-management-checkpoints-v1`, version 1, has store `checkpoints`, key
`active`. Its version-1 head contains a random commit token, current checkpoint,
and previous valid checkpoint. Each checkpoint contains the exact save, SHA-256,
Rust schema/profile/fixture/session/revision identity and a random host session ID.
Every successful explicit load/reset/fixture import starts a fresh host session,
even when a Rust profile reuses its deterministic session ID or revision zero.

Publication checks the previously observed commit token and replaces the head in
one read/write transaction. Only transaction completion confirms durability;
request success does not. An aborted/quota/denied write leaves the previous head.
Another tab with a stale token fails visibly and must reopen/recover. It cannot
silently replace a newer checkpoint. Single-queue ordering prevents an older
asynchronous write from landing after a later import/reset/profile change.

Recovery verifies hash and identity and loads through Rust in a separate WASM
instance before replacing the active world. A corrupt/unsupported current save
falls back to the previous independently validated checkpoint and reports that
fallback. Both invalid checkpoints remain retained and cause a visible failure.
A storage retry never discards accepted in-memory commands. There is no automatic
repair or reference-fingerprint admission. Browser transaction commit provides
the browser's durability guarantee; physical media/power-loss guarantees are
outside this bounded contract.

Acceptance covers current legacy, synthetic manager and private captured-manager
profiles: real Chromium close/reopen, exact native continuation/deduplication,
atomic transaction abort, corrupt/unsupported saves, storage errors, interrupted
writes, ordered import/reset races and concurrent-tab stale writer rejection.
Failure injection is reported separately from ordinary browser execution.

## Executed current-profile result

[Chromium 148 receipt](evidence/pc-r6-storage-v1.json) records successful persistent
browser close/reopen and exact native state/events/records/save/continuation for
all three admitted v1/v2 profiles, including the private captured-manager fixture.
Actual IndexedDB abort, corrupt/unsupported checkpoint fallback, interrupted
uncommitted transaction, delayed command/import/reset and concurrent-tab fencing
passed. Denial and quota exceptions were injected at storage API boundaries;
the failed CDP quota-override experiment (quota reported 1, IDB writes admitted)
is retained explicitly. Actual disk exhaustion remains unqualified.

Commands: Node 22.22.2 `npm run typecheck`, `npm run build`, `npm run check`,
`npm run check:storage`, with the installed Playwright/Chromium and private fixture
locator. Existing 105 native/browser operations remain byte-identical, including
legacy v1 exports and v2 continuation. The reference UI check now waits for import
completion even when a previously persisted manager is already visible.
Baseline 63 workspace Rust tests and native/WASM builds passed before host edits;
Rust source/save formats are unchanged by this increment. Independent review and
exact-head CI/merge disposition are recorded in the delivery PR.
