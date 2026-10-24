# Verification and research validity

## Prevent common-source false confidence

An original-function emulator, Bosman translation and Rust implementation can share mistakes if they use the same wrong setup or decoder. For selected critical behaviours cross-check observations in the actual original Windows process. Record the source of every expected result and any shared code in capture/decoder/comparison. A passing Bosman-to-Rust test with no original evidence is useful but has a narrower authority label.

Record supported fixtures and valid state preconditions. Randomly mutating raw bytes can generate impossible states and misleading rules. Prefer original UI-generated states, controlled commands and validated domain changes. If synthetic invalid states are used for robustness, keep their verdict separate from faithful gameplay behaviour.

## Experiments that can falsify a claim

Each proposed rule includes at least one plausible alternative and a test that distinguishes them. Vary one factor where possible, then test relevant interactions; preserve initial state, RNG and path identity. A trace correlation suggests a dependency; targeted input intervention plus side-effect analysis supports causality. Retain a known false hypothesis as a negative control for the evidence pipeline.

For microcases observe return values, flags when relevant, memory writes, allocation effects and RNG consumption. For journeys observe ordered events, state projections and all known side effects. Unknown/unparsed state remains counted. Instrumentation neutrality tests compare observed state and outcomes, not only whether both processes exit successfully.

## Statistical comparisons

Write metric definitions, population, sampling unit, seed policy, exclusions, effect-size tolerances and stopping rule before a campaign. Confidence intervals alone do not imply equivalence; use an equivalence criterion tied to a justified practical tolerance. 'No significant difference' is insufficient. Match-level observations within one career are dependent: aggregate by independent world/seed or use an appropriate clustered analysis.

Paired seeds reduce variance only while scenarios and RNG consumption remain meaningfully aligned. Distinct RNG schedules may invalidate that pairing. Separate tuning/diagnostic campaigns from a frozen confirmation corpus and correct for planned multiple comparisons. Adaptive exploration is useful for discovery; its selected samples cannot be reported as an unbiased world-wide distribution.

Retain failed/missing cases and explain their effect on estimates. Do not discard a crash or outlier because it spoils the expected average. Size confirmatory samples from pilot variance, intended sensitivity and resource budget; 100 matches is a pilot, not a universal acceptance size.

## Executable falsification tests

Inject a changed numeric result, reordered event, extra RNG draw, omitted state field, corrupt save and dropped trace segment. The comparator must detect or report inability to compare each mutation. Test the normaliser against deliberately changed semantic fields so broad masks cannot turn failures into equality. A counterexample reducer must preserve the original failure predicate and valid state; retain the full parent run when a smaller valid case cannot be found.

## Research productivity gates

For P03, triage 20 functions across at least four domains and deliver at least five reviewed experiment-supported contracts across at least two domains, each with a replayable input and original-backed evidence at its stated level. The remainder may be unresolved with precise next experiments. Demonstrate rejection of a known unsupported claim and generation of a replayable failure bundle. These pilot numbers measure whether the process works, not whole-game completion.

Queue review work separately from raw experiment results. Report pending-review age and accepted findings per reviewer-hour. When pending review exceeds the configured capacity, reduce hypothesis generation and prioritise reproducers/regressions. Do not spend indefinitely producing unreviewable candidate labels.

## Operational qualification

The 24-hour lab pilot requires every attempt accounted for, zero silent result loss, successful intended endpoints for the startup/load, short world-advance and targeted match scenario classes, plus correctly recorded injected worker failure and replay. Test that each sampled detailed/quick fixture used the expected path. Do not accept a campaign in which all jobs are classified failures.

A separate 72-hour continuous-operation gate requires the P01 worker, P02 calibrated corpus, resource caps, lease/cancellation tests and a demonstrated backup restore. Store exact workload, successful/failed/censored counts and resource observations. Run this alongside early Rust work. Clock duration is an operational test, not evidence of semantic completeness.

## Whole-game release

Expand the coverage register before declaring completeness. Each supported competition format and original play mode has an explicit scenario set. Include sustained management, active and holiday AI, original-save import variants, original assets/localisation, multi-season and international boundaries, large worlds and human acceptance. A representative two-season game is an intermediate milestone only. A release report names unsupported configurations and accepted deviations; it must not imply universal bit-identical careers from a finite corpus.
