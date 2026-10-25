# PC-R6 browser checkpoint contract

The host stores the exact Rust slice-save string. Rust continues to own admission,
rules, serialization, replay validation, events and command deduplication. This
initial increment changed neither profile nor v1/v2 slice-save formats. Later
v3/v4 profiles use the same host contract, as recorded below. IndexedDB is
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

Current-profile delivery merged in [PR #34](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/34),
merge `3248e75b12a06919504c743c54dcedb1255af21f`, after independent Astra/high
review of final head `762ed06c145b6b6abc21d4d3ce72eba12ea20d40` and all four
frozen CI checks. Review found and verified a retry-token rebinding fix: after an
initial storage-open failure, a tab cannot adopt another tab's newly published
session token on a late publication retry. The browser regression compares the
entire retained head. The additive R4 v3 profile uses this same host contract.

The [fresh human admission](PC_R4_HUMAN_REGISTRY.md#independently-reviewed-fresh-fixture-admission)
adds another exact fixture to the same v3 profile. Its six-fixture actual-browser
recovery receipt preserves the previous five results and adds fresh corruption/
abort recovery and retained/fresh import races with identical profile/session
names. Storage schemas, worker logic and save formats are unchanged.

The [v4 producer recovery receipt](evidence/human-registry-producer-storage-v1.json)
extends actual persistent browser close/reopen and native continuation to nine
fixtures. All six prior stored results remain unchanged. Mixed producer/selector
deduplication, corrupt-current fallback, visible accepted-but-unsaved state after
an actual transaction abort, and retained/fresh same-profile writer fencing pass.
The [matching browser receipt](evidence/human-registry-producer-browser-v1.json)
contains 375 exact native/Chromium operations, retaining the earlier 204 hashes.
This supplements the historical three- and six-fixture results above; storage
schema and recovery rules remain unchanged.

## Additional negative recovery acceptance

Malformed head metadata fails before any checkpoint is admitted. With valid
head metadata but two invalid checkpoints, recovery records the observed token
but admits neither save. Both failures retain the complete stored head and leave
the active Rust world unchanged; a new worker therefore keeps its default world.
Accepted in-memory commands remain usable and exportable, while publication
retries fail visibly until recovery/storage conditions permit publication. A
newer token cannot be adopted through a publication retry; explicit recovery is
required to rebind to another tab's publication.

`check-invalid-storage.cjs` freezes direct regressions for those existing rules:
actual persistent IndexedDB malformed heads and two invalid checkpoints, visible
failure, full private-byte retention, existing and startup memory, accepted
commands and publication retries, concurrent writer fencing and explicit recovery.
These cases change no host recovery semantics. Execution evidence will be linked
after the additive acceptance run.
