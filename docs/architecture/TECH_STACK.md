# Technology decisions

Decision date: 24 October 2026. Rust is the user's selected implementation language. Exact dependency patches, container digests and compiler version are locked during P0/P1 after a reproducible build; floating `latest` dependencies are prohibited in experiments.

| Component | Decision | Reason / boundary |
|---|---|---|
| Reconstructed whole-game core | Rust workspace; stable pinned toolchain; explicit fixed-width types | Shared native and browser behaviour; readable domain code and controlled arithmetic |
| Native simulator and lab CLI | Rust | Own job execution, manifests, comparison and worker lifecycle |
| Lab service | Rust, Tokio, Axum | Async orchestration/API; CPU-heavy simulation runs in bounded child processes, outside request handlers |
| Durable scheduler and evidence index | PostgreSQL 18, SQL migrations; SQLx | One transactional system for jobs, leases, findings and artifact metadata; no Redis requirement |
| Artifact bytes | SHA-256 content-addressed files on a dedicated volume initially; storage interface permits S3 later | Large saves/traces stay outside database rows; atomic publish and immutable objects |
| Browser game and lab dashboard | React + TypeScript + Vite; pinned pnpm workspace | Familiar UI; separate game and lab apps sharing view/protocol types |
| Browser engine | Same Rust core, `wasm32-unknown-unknown`, wasm-bindgen, dedicated Web Worker | Responsive browser; OS-dependent services remain outside core |
| Wire and scenario contracts | Versioned JSON Schema; JSON envelopes/NDJSON events; binary artifacts by hash | Reviewable, language-neutral boundaries; large state never repeatedly serialised through JSON |
| Rust serialisation | Serde with explicit schema versions | Convenient adapters; serialised struct layout is not the save compatibility contract |
| RE automation | Python, Ghidra headless, Capstone, Unicorn; original Windows debugger for difficult cases | Reuse proven upstream tools; targeted function execution before whole-game substitution |
| Baseline execution | Pinned Bosman native Linux process; original Windows process on the calibrated PC through the reviewed medium helper | Bosman throughput and original behaviour have distinct authority; WSL never launches the original |
| Tests | cargo test, proptest for domain invariants, Criterion for selected benchmarks; Playwright for UI; Python upstream tests | Evidence-driven tests, including native/WASM replay and malformed imports |
| VPS operations | Linux x86-64 first, Docker Compose and systemd supervision | Small operational footprint, isolated processes and resource controls |
| Metrics | Structured tracing/logs plus Prometheus-format counters; dashboard in lab app initially | Queue health and research value visible; add Grafana only if useful |
| CI | GitHub Actions for public synthetic tests, formatting, linting and build checks | Private fixtures on separately controlled workers, never exposed to arbitrary public PR code |

## Upstream dependencies

[cm0102-bosman-edition](https://github.com/maxevans60/cm0102-bosman-edition) supplies the initial native execution and research infrastructure. [cm0102-function-map](https://github.com/maxevans60/cm0102-function-map) supplies the starting address/global catalogue. Both are pinned separately from our Rust workspace; see [integration details](../research/UPSTREAM_INTEGRATION.md).

## Rust boundaries

Long-term workspace boundaries (create only as needed, not all on day one): `compat` (numeric/RNG/address semantics), `game-data`, `game-core`, `game-save`, `game-protocol`, `game-wasm`, `lab-protocol`, `lab-runner`, `lab-compare`, `lab-store`, `lab-api`, `lab-cli`. Browser apps: `apps/game-web`, `apps/lab-web`. Research adapters: `tools/oracles`, `tools/ghidra`, `tools/import-map`. These are planned paths, not implemented components.

Within `game-core`, begin with modules for calendar, people, clubs, management, competitions, match, news and world. Split crates only when dependency boundaries justify it. Avoid one crate per original function and avoid one universal 'entity/component' rewrite before the actual data is understood.

Use typed IDs and owned record arenas for cyclic player/club/competition relationships. Preserve explicit simulation ordering rather than relying on hash-map iteration, pointer order or allocation order. If the original uses addresses semantically, a dedicated virtual-address compatibility model may be required. Stable Rust IDs alone do not solve that.

Engine contract: command + state + deterministic context -> new state + ordered domain events. Queries return immutable projections. Host supplies persistence, assets and external inputs. Use incremental `advance_until` budgets so browser work can yield. Invalid commands fail without partial mutation. Snapshot/restore includes RNG and scheduling state. The implementation need not be purely functional or clone the entire world per command.

No Tokio, database connection, wall clock or ambient random generator inside deterministic game-core. Use ordinary Rust arithmetic only where its behaviour is explicitly correct; otherwise use wrapping/checked operations and tested conversions. Floating-point/x87 equivalence is measured. No `fast-math` assumption or claim that Rust automatically reproduces original arithmetic.

## Why this split

Rust remains the long-term core language, not a temporary accelerator beneath a second TypeScript engine. TypeScript is retained because it suits browser interfaces. Native/WASM consistency must be tested; the WASM target lacks ordinary host filesystem/thread services, so these are adapters. See official [target documentation](https://doc.rust-lang.org/rustc/platform-support/wasm32-unknown-unknown.html).

Python keeps existing upstream research scripts usable while the durable lab is written in Rust. C remains in the pinned Bosman build and any reviewed instrumentation patch. No wholesale conversion of the upstream translator is necessary to start the lab.

PostgreSQL supports row locking with `SKIP LOCKED`, appropriate for queue consumers, but this is not exactly-once execution. We implement at-least-once attempts with fenced result acceptance and test the failure cases. See [PostgreSQL SELECT](https://www.postgresql.org/docs/18/sql-select.html). SQLite remains acceptable for a throwaway local spike, not a second production scheduler. Kafka, Kubernetes, a graph database and a vector database are deferred until a measured requirement exists.

## Provenance and distribution

The repository is MIT at the inspected base. Bosman's inspected current `LICENSE` is GPLv3; its function map documents CC BY 4.0 terms. Keep separate provenance records and attribution. A process boundary is useful engineering isolation, not a legal guarantee of licensing independence. Before copying/adapting GPL source into this project or distributing a combined build, decide the distribution/licensing approach from the actual proposed artifact. Do not silently relicense copied code as MIT.

Initial default: build Bosman externally from its pinned source; store local paths/digests in private configuration; cite upstream behaviour and tests. Maintain any Bosman instrumentation patch with its own upstream licence. Original executable, RNG table, data, assets and save snapshots remain private inputs. Synthetic public fixtures are distinct and never presented as proof of original behaviour. No requirement to spend money on commercial RE software or on a local GPU.

## Implementation contracts

Use [reconstruction method](RECONSTRUCTION_METHOD.md), [runtime contracts](RUNTIME_CONTRACTS.md), [verification plan](../research/VERIFICATION_PLAN.md) and the [bootstrap checkpoints](../roadmap/BOOTSTRAP.md) to turn these decisions into bounded executable work.
