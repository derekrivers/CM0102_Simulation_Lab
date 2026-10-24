# Sources, repository state and limitations

Inspected 24 October 2026. These are source inspections, not reports of tests executed in this planning session.

## Pinned repositories

- Target [CM0102_Simulation_Lab](https://github.com/derekrivers/CM0102_Simulation_Lab/tree/b702984020767bd36095dc231354a77a97a9c2ff), commit `b702984020767bd36095dc231354a77a97a9c2ff`: only `README.md` and `LICENSE` at this base. No `AGENTS.md`, roadmap, closure reports, planner, ticket registry, application or tests.
- [Bosman Edition](https://github.com/maxevans60/cm0102-bosman-edition/tree/144ed82c248228c7769c6785899527eae5b33c3d), commit `144ed82c248228c7769c6785899527eae5b33c3d`.
- [Function map](https://github.com/maxevans60/cm0102-function-map/tree/2bb558ef6a6bcdbd304dd1a6a4cf156c6707007c), commit `2bb558ef6a6bcdbd304dd1a6a4cf156c6707007c`.

## Inspected upstream evidence

| File | Observation used in this plan |
|---|---|
| [full_play_run.py](https://github.com/maxevans60/cm0102-bosman-edition/blob/144ed82c248228c7769c6785899527eae5b33c3d/tests/seasons/full_play_run.py) | SDL dummy drivers, seed and fixed-clock settings, engine-on holiday runs, periodic save/reload; inherits environment and contains Mac-specific load/HOLD scheduling |
| [soak_run.py](https://github.com/maxevans60/cm0102-bosman-edition/blob/144ed82c248228c7769c6785899527eae5b33c3d/tests/seasons/soak_run.py) | Quick-result long campaigns via season-jump switch, periodic save/reload; distinct from detailed match testing |
| [season_report.c](https://github.com/maxevans60/cm0102-bosman-edition/blob/144ed82c248228c7769c6785899527eae5b33c3d/src/recomp_rt/win/season_report.c) | Documents the season-jump quick-simulation path and competition updates |
| [cases_random.py](https://github.com/maxevans60/cm0102-bosman-edition/blob/144ed82c248228c7769c6785899527eae5b33c3d/tests/diff/cases_random.py) | Original routine execution in Unicorn, MSVC/table RNG state and x87 control setup; seed 0 has time-dependent handling |
| [TESTING.md](https://github.com/maxevans60/cm0102-bosman-edition/blob/144ed82c248228c7769c6785899527eae5b33c3d/docs/TESTING.md) | Same-save testing, memory-layout effects, release/season/screen sweeps, large-save considerations |
| [LICENSE](https://github.com/maxevans60/cm0102-bosman-edition/blob/144ed82c248228c7769c6785899527eae5b33c3d/LICENSE) | Current inspected Bosman licence is GPLv3 |
| [Map README](https://github.com/maxevans60/cm0102-function-map/blob/2bb558ef6a6bcdbd304dd1a6a4cf156c6707007c/README.md) | Named functions and global catalogue, confidence interpretation and provenance; imported names are not our verified contracts |

Upstream reports are upstream assertions until reproduced locally. This planning session did not build Bosman, run CM01/02, inspect a supplied original binary, benchmark the VPS, or invoke Jev. Function addresses in upstream tooling identify research starting points; read the actual original routine before relying on its claimed contract.

The forum URL supplied earlier, https://champman0102.co.uk/viewtopic.php?t=11024, was not fully retrievable in the earlier research. Repository evidence, rather than an assumed reading of all forum replies, grounds this plan.

## Official technology references

- Rust WASM target: https://doc.rust-lang.org/rustc/platform-support/wasm32-unknown-unknown.html
- Explicit integer operations: https://doc.rust-lang.org/std/primitive.u32.html
- Tokio: https://docs.rs/tokio/latest/tokio/
- Axum: https://docs.rs/axum/latest/axum/
- PostgreSQL row locking: https://www.postgresql.org/docs/18/sql-select.html
- Container resource limits: https://docs.docker.com/engine/containers/resource_constraints/
- Ghidra: https://github.com/NationalSecurityAgency/ghidra
- Unicorn: https://www.unicorn-engine.org/
- Jev: https://docs.typesafe.ai/introduction ; https://docs.typesafe.ai/introduction/coding-agents ; https://docs.typesafe.ai/confidence ; https://docs.typesafe.ai/models ; https://docs.typesafe.ai/api/system-one ; https://docs.typesafe.ai/model-jaggedness/jev-1.13

Architecture, phase ordering, sizing envelopes, budgets and gates are design recommendations. They are not measured performance claims or upstream guarantees.
