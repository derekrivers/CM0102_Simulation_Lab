# Whole-game reconstruction roadmap

## Foundational upstream projects

This project builds on Max Evans's existing work:

- [cm0102-bosman-edition](https://github.com/maxevans60/cm0102-bosman-edition): our initial native execution backend, recompiler/runtime reference and source of reusable headless and differential test infrastructure.
- [cm0102-function-map](https://github.com/maxevans60/cm0102-function-map): our starting function/global inventory, names, provenance and call/data relationship clues. Import it in P00; add our evidence rather than starting a blank map.

[Upstream integration](docs/research/UPSTREAM_INTEGRATION.md) specifies pins, exact inputs, adapters, test reuse, map ingestion and upgrade qualification. The original executable remains the behavioural reference. Neither upstream project is treated as automatically complete or infallible.

**Outcome:** a faithful, playable and extensible reconstruction of the entire CM01/02 game. **Rust** implements the game and simulator; **React/TypeScript** implements the browser interface. The continuous VPS laboratory supplies reproducible evidence and verification throughout.

Planning base: `b702984020767bd36095dc231354a77a97a9c2ff`. This is a standalone project roadmap. All phases are planned; nothing here claims a built simulator or deployed VPS.

| Phase | Outcome | Depends on |
|---|---|---|
| P00 | [Baseline and programme contract](docs/roadmap/phase-00.md) | — |
| P01 | [Reliable headless laboratory](docs/roadmap/phase-01.md) | P00 |
| P02 | [Calibrated references and replay](docs/roadmap/phase-02.md) | P00 |
| P03 | [Continuous evidence and function mapping](docs/roadmap/phase-03.md) | P01, P02 |
| P04 | [Rust foundation and browser vertical slice](docs/roadmap/phase-04.md) | P02 |
| P05 | [People and club management](docs/roadmap/phase-05.md) | P04 |
| P06 | [Detailed and quick match reconstruction](docs/roadmap/phase-06.md) | P04 |
| P07 | [Competitions and complete world lifecycle](docs/roadmap/phase-07.md) | P05, P06 |
| P08 | [Complete playable application](docs/roadmap/phase-08.md) | P07 |
| P09 | [Whole-game fidelity and compatibility release](docs/roadmap/phase-09.md) | P08 |
| P10 | [Extensible game and sustained development](docs/roadmap/phase-10.md) | P09 |

P00 establishes the inventory and inputs. P01 builds reliable operations while P02 calibrates references locally. P04 proves the shared native/browser core after P02, in parallel with P03 continuous research; Jev never blocks Rust development. P05 and P06 are genuine parallel implementation lanes, converging in P07. UI and persistence work begin in P04 and accompany every slice; P08 completes the experience. P09 closes the original scope. P10 delivers extended gameplay. Extension interfaces are designed early, but feature development cannot silently alter the faithful baseline.

See [implementation sequence and gates](docs/roadmap/implementation-roadmap.md), [simulator design](docs/architecture/SIMULATOR.md), [VPS operation](docs/operations/VPS.md), [Jev trial](docs/architecture/JEV.md), and [non-negotiables](docs/NON_NEGOTIABLES.md).

No calendar completion date is credible before the P01/P02 throughput and compatibility work. Use gate-based commitments; re-estimate after the first original-referenced Rust slices. Continuous compute accelerates observations, not necessarily semantic understanding or reviewer throughput.

Start with the [bootstrap checkpoints](docs/roadmap/BOOTSTRAP.md). The [pre-implementation review](docs/reviews/PRE_IMPLEMENTATION_REVIEW.md) records the substantive gaps found and their resolution.
