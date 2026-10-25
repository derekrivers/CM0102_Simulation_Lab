# CM0102 Simulation Lab

Reconstruct the entire Championship Manager 01/02 game with **Rust** for behaviour and persistence, and **React/TypeScript** for browser presentation. The official 3.9.68 executable and original 2001 data are the initial behavioural reference. This is an early research and implementation project; a Rust game or playable browser simulator does not exist yet.

## Start here

- [Roadmap](ROADMAP.md): current priorities and whole-game scope.
- [Active PC delivery plan](docs/roadmap/PC_FIRST.md): next tasks, acceptance tests and stop conditions.
- [Progress and known gaps](docs/status/PROGRESS.md): demonstrated results versus pending work.
- [Documentation index](docs/MANIFEST.md): contracts, evidence and historical material.

The PC is the primary development and reference host. Use WSL/Linux for the existing lab CLI and Bosman builds. The future portable Rust core will run natively and in WASM. Live Windows reference execution follows the separately reviewed [PC medium-helper contract](docs/architecture/PC_MEDIUM_HELPER_QUALIFICATION_V1.md); WSL must not launch the original game.

## What works today

The pinned map importer, qualified official input inventory, bounded Bosman adapter and synthetic comparator exist. One controlled fixed-clock, seed-1, 14-game-day Bosman same-save replay has retained evidence. Windows host probes and no-UI launcher builds have evidence, but the Lab has not qualified original-process execution or original/Bosman parity.

[Reversal research](docs/research/REVERSAL.md) now supplies a freshly reproduced official-instruction RNG oracle. **Next: port the CRT and small-bound RNG to Rust, execute it natively and in WASM, and prove checkpoint continuation.** Full Windows qualification does not block this scoped numeric work.

## Source layout

| Path | Role |
|---|---|
| `crates/lab-cli` | Existing Linux host tooling: inventory import, process supervision, Bosman adapter and comparator |
| `config` | Pinned inputs, profiles and verification contracts |
| `tools/windows` | Host probes, harmless fixtures and frozen dormant launcher controls; see [status](docs/history/README.md) before using |
| `docs` | Active plan, evidence, architecture and long-term phase contracts |

The Linux lab uses Unix process/filesystem APIs; do not build it as the browser game engine. A small portable compatibility crate is the next implementation increment, not an existing component.

For development in a WSL-native checkout, install the toolchain pinned in `rust-toolchain.toml`, then run:

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo build --locked
cargo test --locked
```

These are developer commands, not a claim that Rust is already installed on the PC. CI also runs frozen Linux/Windows verification checks. No original game files are required for public synthetic tests.

The importer accepts the exact locked map checkout:

```sh
cargo run -p lab-cli -- import-map \
  --source-dir /path/to/cm0102-function-map \
  --lock-manifest config/upstream-lock.json \
  --executable /private/path/to/cm0102.exe \
  --output target/b0-evidence/function-map-import.json
```

Omitting `--executable` permits map-only work and leaves address validation pending. Imported names remain hypotheses.

## Sources and boundaries

Max Evans's [Bosman Edition](https://github.com/maxevans60/cm0102-bosman-edition) provides the separately qualified native execution/research backend; his [function map](https://github.com/maxevans60/cm0102-function-map) supplies the starting inventory. [Reversal](https://github.com/derekrivers/Reversal) is a pinned research reference, not a second production engine. See [upstream integration](docs/research/UPSTREAM_INTEGRATION.md), [attribution](docs/research/UPSTREAM_ATTRIBUTION.md) and [non-negotiables](docs/NON_NEGOTIABLES.md).

Original executables, assets, data, saves and private captures stay outside public Git. This repository's MIT licence does not relicense upstream material. VPS upgrades, continuous campaigns, dashboards and model pipelines are deferred until demonstrated work needs them.
