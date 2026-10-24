# CM0102 Simulation Lab

## Foundational upstream projects

This project builds on Max Evans's existing work:

- [cm0102-bosman-edition](https://github.com/maxevans60/cm0102-bosman-edition): our initial native execution backend, recompiler/runtime reference and source of reusable headless and differential test infrastructure.
- [cm0102-function-map](https://github.com/maxevans60/cm0102-function-map): our starting function/global inventory, names, provenance and call/data relationship clues. Import it in P00; add our evidence rather than starting a blank map.

[Upstream integration](docs/research/UPSTREAM_INTEGRATION.md) specifies pins, exact inputs, adapters, test reuse, map ingestion and upgrade qualification. The original executable remains the behavioural reference. Neither upstream project is treated as automatically complete or infallible.

A research and reconstruction programme for the **entire Championship Manager 01/02 game**: a faithful playable game, understandable source, and deliberate extensions.

The laboratory is the first enabling product. It runs repeatable experiments against the original game and a pinned Bosman build, records evidence, and verifies the replacement. The reconstructed game and simulator use **Rust**. The browser interface uses **React and TypeScript** with the Rust core compiled to WebAssembly. Python supports existing reverse-engineering tooling.

Status: P00/B0 inventory and B1 execution work are active, 24 October 2026. The pinned public function/global map has a deterministic Rust importer and reconciled provenance report. The supplied executable is the exact official 3.9.68 PE32 expected by the pinned Bosman source, and all imported addresses have been validated against its sections. The pinned Bosman source builds successfully and all 45 registered upstream tests pass. The official ISO and patch have now produced a separate private 760/760 clean runtime set; two clean upstream smoke runs passed through first news and holiday advancement. A bounded local process contract validates execution requests and protocol evidence, but the Bosman-specific protocol adapter is still outstanding. The user's existing installed folder remains modified and untouched. No protocol-qualified Bosman replay job, VPS service, or reconstructed engine exists yet.

Start with [ROADMAP.md](ROADMAP.md), [non-negotiables](docs/NON_NEGOTIABLES.md), [stack decisions](docs/architecture/TECH_STACK.md), and the [simulator design](docs/architecture/SIMULATOR.md). The detailed [implementation roadmap](docs/roadmap/implementation-roadmap.md) links all phase gates. [Sources and limitations](docs/research/SOURCES.md) distinguish inspected code from proposed behaviour.

Current implementation and blockers are recorded in [programme progress](docs/status/PROGRESS.md). To import a checkout of the exact locked function-map revision:

```sh
cargo run -p lab-cli -- import-map \
  --source-dir /path/to/cm0102-function-map \
  --lock-manifest config/upstream-lock.json \
  --executable /private/path/to/cm0102.exe \
  --output target/b0-evidence/function-map-import.json
```

The generated evidence artifact is intentionally untracked. It retains every imported row as an upstream hypothesis. Omit `--executable` only for map-only work; the artifact then explicitly reports address validation as pending.

The versioned local execution request and child protocol are documented in [local execution request v1](docs/architecture/EXECUTION_REQUEST_V1.md).

Whole-game scope includes management, world simulation, competition rules, match engines, databases, save/load, news, navigation, presentation, settings and supported modes. Match fidelity is one workstream.

The existing MIT licence is retained for this repository. Upstream material has its own terms; see the [provenance decision](docs/architecture/TECH_STACK.md#provenance-and-distribution). No original executable, game assets, databases or saves are included.
