# Jev for research triage

Decision: include a bounded evaluation in P3; promote to optional production routing only if it improves our measured research workflow. Rust still owns simulation, scheduling, verification and all game behaviour. A TypeSafe service outage must not stop deterministic experiments.

## Verified capability and fit

TypeSafe describes Jev as a model for structured decisions over supplied state. Choice returns an option and distribution; Score uses a defined rubric; Noul returns a yes-probability. Jev does not generate explanations or Rust code, operate Ghidra, maintain a durable queue, or replace a coding agent. These distinctions come from the [introduction](https://docs.typesafe.ai/introduction) and [coding-agent documentation](https://docs.typesafe.ai/introduction/coding-agents), inspected 24 October 2026.

Its best role here is a small decision service fed with well-prepared evidence. A generative/reasoning model or engineer investigates complex disassembly and proposes contracts. Jev can help route those candidates; executable tests establish whether the behaviour holds.

| Proposed task | Input prepared by our code | Jev output | Authority |
|---|---|---|---|
| Subsystem triage | Strings, caller labels, observed fields, concise reviewed context | Choice: contracts / transfers / training / competitions / match / UI / persistence / unknown | Candidate label only |
| Failure triage | Parsed first divergence and known signature candidates | Choice among shortlisted known categories, new, insufficient evidence | Queue routing; never discard the failure |
| Review prioritisation | Missing evidence, upcoming dependency and existing reproducer summary | Separate rubric scores for relevance and ambiguity | Rust combines with measured cost/coverage |
| Evidence relevance | One candidate claim and a small source excerpt | Supports / contradicts / insufficient | Reviewer aid; no claim promotion |
| Next experiment | Finite list of approved templates with preconditions | Choice or abstention | Scheduler verifies capabilities, limits and preconditions |

Missing field detection, hashes, numeric differences, coverage counts, budgets, date comparisons and rule-based duplicate detection are deterministic code. Ask Jev only about residual semantic ambiguity. No Jev call in the match loop or faithful gameplay path.

## Integration

Implement a Rust HTTP adapter behind `ResearchTriageProvider`; the documented API is `POST https://api.typesafe.ai/v1/systemone` with bearer authentication, model, state and named questions. This avoids requiring a Rust SDK. Validate response keys/types/ranges and chosen options. Store request digest, full allowed request/response, criteria version, model ID, latency, token usage and routing action. Provider secrets stay in server configuration.

The [models page](https://docs.typesafe.ai/models) currently lists `jev-1.14.0`. Use a versioned model ID after verifying account availability; avoid moving aliases in a calibrated campaign. Published prices and rate limits must be rechecked at deployment; no spending commitment is made here. The [API reference](https://docs.typesafe.ai/api/system-one) defines usage reporting. Cache by model, question, criteria and state digests; log actual service responses because repeat inference is not assumed deterministic.

Batch independent atomic questions about the same compact evidence packet. Dependent questions use a subsequent request. Do not send complete executables, saves or enormous traces. Allowlisted extracted metadata and approved snippets only; provider input policy is a configuration decision before live use. Respect timeouts and `Retry-After`, cap attempts, and use a circuit breaker. On failure, deterministic queue priorities continue and uncertain items remain reviewable.

## Validation and promotion gate

Create a manually labelled corpus starting with 300 distinct evidence packets across subsystems and failure types; this is a pilot size, not proof of calibration. Partition by function/failure family to prevent near-duplicate leakage, with a reserved held-out test split. Labels come from inspected code and accepted experiments, not another model's unsupported answers. Include unknown/ambiguous packets and shuffled option-order checks.

Compare rules-only routing, Jev routing, and any existing reasoning-model triage on the same corpus. Measure per-class precision/recall, abstention coverage, wrong-route severity, time to a useful experiment, cost, latency and review burden. A proposed starting gate is at least 95% observed precision for low-risk automatic routing with confidence intervals reported; sparse categories remain manual until enough evidence exists. Never use that threshold to accept a function contract. Final thresholds are calibrated per task on validation data and tested once on the held-out set.

Run in shadow mode first. Record suggested decisions while the deterministic baseline schedules work. Promote only if useful-result yield or review time improves without unacceptable routing errors. Sample promoted decisions for continued review and requalify after a model/criteria change. Preserve exploration and mandatory regression budgets regardless of scores.

TypeSafe's [confidence documentation](https://docs.typesafe.ai/confidence) defines confidence from the answer distribution. It is not an external proof of correctness on x86 reverse engineering. The [Jev 1.13 limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) specifically caution about numerical precision, indirection and low-level representations; these are version-specific warnings that motivate testing the chosen model on our actual corpus, not claims that all newer versions fail identically.

## Explicit exclusions

Jev cannot certify function semantics, approve golden results, change comparison tolerances, choose arbitrary shell commands, merge code, or decide a game outcome in faithful mode. A model returning a typed value guarantees a usable shape, not a correct fact. General-purpose reasoning support remains a separately configured service with its own budget. The entire lab works with both model services disabled.
