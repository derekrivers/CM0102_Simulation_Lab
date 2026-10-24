# Runtime and persistence contracts

These are implementation requirements, not claims of existing APIs. P01/P04 turn the contracts into versioned schemas and contract tests before relying on them.

## Process protocol

Rust supervisor communicates with backend adapters through framed/versioned JSON messages, with NDJSON acceptable for low-volume records. Stdout is protocol-only; diagnostic logs use stderr or separate artifacts. Each frame has protocol version, attempt ID, sequence, message kind and bounded payload length. Large snapshots/traces are artifact references with digest, length and content type. Reject malformed/oversize messages, invalid ordering and protocol mismatch explicitly.

Handshake reports backend identity and capabilities. Then configure input/profile, prepare/load fixture, execute ordered commands, emit progress/checkpoints, collect artifacts and finish with a terminal execution record. Human-input scripts for the original/Bosman backend are adapter details; do not imply they support the same internal stepping granularity as the Rust core.

Game commands carry session ID, command ID and expected state revision. A duplicate ID with identical payload returns the recorded result; a duplicate with different payload is rejected. Stale revisions do not partially mutate state. Serialise command acceptance and mutation inside one world. Separate transport retry from replaying a game action. Preserve deduplication scope across checkpoint/recovery or clearly reject replay beyond the supported window.

## Execution versus comparison

Execution status: queued, leased, running, collecting, succeeded, failed, cancelled. A terminal reason adds completed-target, crash, timeout, stall, invalid-input, unsupported-capability or infrastructure-error. Comparison verdict is a separate field: not-run, equal, different, inconclusive or not-comparable. A completed process can have a different verdict; a crash is not a valid equal comparison just because both processes crash.

Require the declared stop condition, expected path, artifact hashes and scenario assertions before recording execution success. Exit code zero alone is insufficient. For seasons, assert the intended calendar/competition boundary; a fixed 365-day leg is not automatically an exact season transition. Record unexpected dialogs, missing saves and truncated traces. Track missing/censored runs in campaign statistics.

## Lease and resource fencing

Database fencing prevents stale result publication, not duplicate CPU use. Each attempt also owns a host execution slot and process group. On lease loss the supervisor drains/stops its child after a bounded grace period. A replacement requires a free measured slot; a partitioned old worker may still exist until its lease-loss policy fires. Host cgroup limits bound combined resource use. Test old-worker late completion, lease loss during collection, and cancellation versus completion races.

Keep mandatory baseline regressions separate from optional research ranking. Scheduler/worker time uses host monotonic deadlines for watchdogs; game time comes from deterministic simulated context. No host scheduling clock may advance the game calendar implicitly.

## Save and checkpoint formats

Distinguish original save files, process/function snapshots, and new Rust game saves. They have different compatibility guarantees. Every format has magic/schema version, payload length/checksum, engine/rules profile, data identity, feature versions and required capabilities. New saves include complete deterministic RNG/scheduler state and stable entity IDs. Original-memory snapshots also identify address/layout/backend assumptions.

Use a documented, explicitly versioned binary payload for large state, with JSON metadata/manifest. Choose the codec after representative memory/size benchmarks; Serde alone is not a stable format specification. Avoid uncontrolled peak-memory copies during decode, save, compression or JS/WASM transfer. Validate untrusted lengths and referential integrity before allocating/committing a world. Reject unsupported versions and preserve the previous save on failure.

Migration is a pure versioned transformation with before/after fixture tests and an immutable backup. No live silent profile migration. A missing extension/version produces a clear failure or an explicit tested migration. Original-save export remains separately scoped; original import needs its own coverage matrix and unknown-byte accounting.

## Browser host

Use one Rust WASM instance in a dedicated worker initially. UI receives projections/deltas rather than a full mutable world mirror. Define buffer ownership/lifetime; do not retain stale JS views across WASM memory growth. Pass u64 identifiers/counters as schema-safe strings or explicitly supported BigInt encodings, not lossy JS Number conversions. Currency/game arithmetic remains Rust-owned.

Use bounded work slices for advancing simulation and publish committed checkpoints. Cancellation happens at an explicit safe boundary; rendering pause or a throttled tab must not change game outcomes. Test worker crash, tab reload, storage quota failure, application upgrade during a career and recovery from the last complete checkpoint.

Proposed browser storage: IndexedDB metadata with chunked state records initially; evaluate OPFS for large payloads during P04. Keep portable file export/import available. Persist through transactional metadata/payload publication and retain the previous valid snapshot. Browser storage is quota-limited and may be evicted; it is not the user's only backup. See [storage guidance](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria) and [WASM memory](https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/JavaScript_interface/Memory).

Measure total browser working set, including WASM memory, decoded records, UI projections and save/compression buffers, on representative single-nation and all-nation/long-career cases. A native build fitting RAM does not establish browser feasibility. Set supported browser/version/device envelopes from results and report unsupported combinations; do not silently remove game features or move simulation to a paid server to hide a failure.

## Contract test set

Version mismatch; unknown capability; duplicate command; stale revision; malformed/oversize frame; interrupted artifact write; lost lease; late completion; missing stop condition; snapshot migration failure; invalid foreign key; oversized import; native/WASM replay; browser refresh/quota failure. These test meaningful state/authority boundaries, not mere serialisation of a struct to itself.
