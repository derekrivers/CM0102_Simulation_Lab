# CM0102 Simulation Lab operating instructions

## Objective and authority

Reconstruct the entire Championship Manager 01/02 game. Rust owns game rules, simulation, persistence semantics, and native/WASM behaviour. React/TypeScript owns browser presentation and must not duplicate game rules. The original official 3.9.68 executable with matching 2001 data is the initial behavioural reference; Bosman is a separately qualified execution platform.

The repository owner authorizes implementation agents to create branches and worktrees, commit and push changes, open and update pull requests, review them, and merge qualified pull requests. This supersedes the roadmap bundle's historical local-planning-commit stopping point. It does not bypass branch protection, tool restrictions, required evidence, or independent review. Experimental workers, model output, and unreviewed generated artifacts may not promote claims, rewrite reference results, merge code, or deploy themselves.

## Delivery rules

- Read `ROADMAP.md`, the active phase contract, `docs/NON_NEGOTIABLES.md`, and nested instructions before editing.
- Preserve unrelated work and private inputs. Never commit original executables, proprietary game data/assets/saves, raw derived fixtures, credentials, or sensitive traces.
- Use the pinned upstream revisions in `config/upstream-lock.json`. Imported names are hypotheses, not verified semantics.
- Deliver small increments with explicit acceptance cases. Run formatting, lint/build, behavioural tests, negative controls appropriate to the change, and an independent review of the exact proposed revision.
- Keep execution status separate from comparison verdict. Never auto-bless goldens, hide divergent fields, invent tolerances, discard failures, or claim a phase gate from scaffolding.
- Refresh against the target branch and repeat affected checks before merging. Record the merge and evidence in `docs/status/PROGRESS.md`.
- Deploy only qualified builds through the documented runbook. Long-running gates require their actual elapsed duration and recovery evidence.

## Agent routing

Use the strongest available coordinator/reviewer for architecture, integration, subtle fidelity, concurrency, save/protocol compatibility, and difficult x86/numeric investigations. Use a fast coding worker for bounded tasks with frozen interfaces and tests. Start with at most two concurrent subagents besides the lead and one CPU-heavy build/simulation budget. Give each agent owned paths, inputs, non-goals, acceptance cases, verification commands, and required evidence. An implementer cannot be the only reviewer of its own change.

Current clients may expose different model names from the preferred roadmap routing. Record the actual model selection or closest available substitution; never claim an unavailable model was used.

## Resource and scientific boundaries

Keep the deterministic core free of ambient wall clock, randomness, networking, filesystem, and database access. Preserve complete RNG and scheduler state where supported. Run reference backends in isolated per-attempt directories with bounded CPU, memory, time, and artifacts. Missing executable/data identity means address validation and original-backed parity remain pending, not passed.
