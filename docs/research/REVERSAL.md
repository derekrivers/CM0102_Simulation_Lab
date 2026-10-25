# Reversal research integration

Inspected and reproduced 25 October 2026 at [revision 9b0d1a5](https://github.com/derekrivers/Reversal/tree/9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345). Simulation Lab remains the primary Rust implementation repository. Select evidence by need; do not merge the repositories wholesale or inherit Reversal's older TypeScript engine direction and execution instructions.

## Accepted input for PC-R1

The CRT/small-bound RNG work uses the same official executable as this lab: 7,192,576 bytes, SHA-256 `0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86`.

Selected sources at that pin:

- [bounded-random.ts](https://github.com/derekrivers/Reversal/blob/9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345/reconstruction/bounded-random.ts): comparison implementation and explicit state.
- [check-random.ts](https://github.com/derekrivers/Reversal/blob/9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345/reconstruction/check-random.ts): retained corpus checks.
- [emulate_random.py](https://github.com/derekrivers/Reversal/blob/9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345/scripts/emulate_random.py): original-instruction oracle generator.
- [random-validation evidence](https://github.com/derekrivers/Reversal/tree/9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345/evidence/random-validation): retained oracle and explicitly synthetic table.

The root retained checker (`node scripts/check-research.mjs`, equivalent to root `npm run check`) passed with Node 24.19.0. It checks retained research and metadata; it does not recreate live Windows captures or browser interaction.

The oracle was independently regenerated against the private hash-verified official executable with Python 3.12.3, Unicorn 2.1.4 and `--synthetic-table`: 71,043 original instructions, 1,024 CRT steps and 2,570 bounded calls. Fresh files matched retained files byte for byte. See the [reproduction receipt](evidence/reversal-rng-2026-10-25.json).

| Artifact | SHA-256 |
|---|---|
| Oracle JSON | `b7794145182f3ee357c11bf53136351c4231b960ae8c69d560ab2732a2d2f692` |
| Synthetic table | `befdec88f802582bba7450e418aaa39837036c8d038810158cfc7a998be1b3db` |

This establishes an input for a scoped port, not full RNG initialization, actual-game table contents, time seeding, the large-bound x87 branch, original saves, game random-call order or original-process parity. The [active plan](../roadmap/PC_FIRST.md) freezes implementation acceptance. No upstream implementation or raw original material is copied by this reset; preserve source licence/attribution when adapting code.

## Useful later, with boundaries

| Material | Reuse decision |
|---|---|
| Clock/event/microhelper contracts and metadata | Select by a concrete feature dependency; preserve partial/unverified labels |
| Action33/keeper investigation | Retain dependency research; unresolved state/callees make the complete penalty resolver a poor first task |
| R41 paired live lookup | Capture-method reference only; private input recovery and specimen-specific qualification required |
| React read-only Squad → Profile → Back viewer | Presentation/view-model reference for a later Rust workflow |
| Fictional React navigation demo | Selected shell/layout reuse only; no engine bindings or real state transitions |
| UI census | 50 screenshot-confirmed states, 111 discovered uncaptured routes and 12 unknown sections; scope inventory, not completion percentage |

[R41's paired-return report](https://github.com/derekrivers/Reversal/blob/9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345/reports/engine-paired-return-41.md) records one cached null-result invocation with nine registers and 1,180 represented stable bytes. Its 85 instructions and 19 ordered memory effects are emulator replay, not a live instruction trace. The checker does not independently authenticate capture provenance; the private capture was not recovered in this review.

That live GDI specimen has SHA-256 `0e50572c292bdfb9de8b3e087dd29043a13bcd0985ed198c9011e5a0f694388b` and uses updated data. It cannot qualify the Lab's official executable/data baseline. Reversal's recorded fresh-process replay differences also remain unresolved. Do not transfer virtual addresses or behaviour claims between specimens without verification.

The [UI demo's own boundary](https://github.com/derekrivers/Reversal/blob/9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345/apps/ui-demo-41/README.md) excludes save loading and game-state changes. Its screens are not reconstructed gameplay. Reversal's main README predates R30–R41 and later UI work; use pinned evidence files, not its headline status alone.
