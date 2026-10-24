# Pre-implementation design review

Reviewed 24 October 2026. Revision 3 incorporates the preceding upstream-integration correction and this full review. Scope: the complete roadmap, phase dependencies, non-negotiables, simulator, evidence model, Rust/browser architecture, upstream reuse, VPS operations, Jev and delivery handoff. This is a design review conducted by the assistant; no independent second reviewer or live game validation is claimed.

## Verdict

Proceed with the bounded bootstrap checkpoints after their actual inputs are available. The design now specifies a credible method for turning original behaviour into tested Rust features and scaling the research loop. It does not prove that every game behaviour has been discovered or that the full rewrite will meet fidelity/performance targets. Those are the research programme's measured outcomes.

The most important change is sequencing: local calibration and a first Rust/browser slice no longer wait for the entire continuous lab or an optional model evaluation. The lab and game now develop together. Whole-game scope remains unchanged.

## Findings and dispositions

| ID | Severity | Finding in the prior draft | Resolution and verification point |
|---|---|---|---|
| R01 | High | Foundational upstream references were buried; map import was late | Prominent direct links and a dedicated upstream integration contract; import in P00 and enrich in P03; idempotent import/count/provenance gate |
| R02 | High | First Rust slice depended on broad mapping automation, potentially including Jev | P02 local calibration can parallel P01 operations; P04 depends on P02, not P03; model trial explicitly optional; graph and phase contracts updated |
| R03 | High | P00 required Bosman startup before the phase that builds the first adapter, obscuring responsibility | P00 owns inputs/source/map qualification; P01/P02 own runtime startup and execution evidence; map-only work can start without game files |
| R04 | High | Investigating 20 functions could pass with zero supported contracts | Require at least five reviewed experiment-supported contracts across two domains plus negative control, within a four-domain triage pilot |
| R05 | High | All failed attempts could satisfy the original 24-hour operational wording | Require successful intended endpoints in three scenario classes as well as no lost results and fault recovery |
| R06 | High | Function-by-function mapping did not define how coupled routines become a coherent Rust feature | Add dependency/ownership graph, cycle grouping, side-effect capture and explicit slice boundary ledger; no implicit mixed-runtime substitution |
| R07 | High | Capture/decoder errors could be shared by both sides of a differential test | Track expected-result authority and shared setup; cross-check selected critical cases in the original Windows process; decoder and deliberate-mutation tests |
| R08 | High | Runtime API, state/save formats and browser resource ownership lacked sufficient contracts | Add protocol/version/command-retry/stop-condition contracts, three distinct snapshot types, safe binary import and early browser working-set/storage tests |
| R09 | Medium | A mismatch was both an execution state and a comparison result | Separate execution lifecycle, terminal reason and scientific verdict; a zero exit or shared crash cannot constitute fidelity success |
| R10 | Medium | Database fencing addressed stale writes but not duplicate computation after a partition | Add host execution slots, lease-loss termination and combined resource limits; qualify cancellation/completion and late-worker races |
| R11 | Medium | Statistical similarity could be interpreted too loosely | Require equivalence criteria, valid sampling units, failed-case accounting and holdout; distinguish adaptive discovery from confirmation |
| R12 | Medium | Full scope was scattered, with browser recovery and data editing insufficiently explicit | Coverage register expanded, early UI/asset inventory, browser quota/recovery checks and validated extension editing workflow; P09 closes feature-level rows |
| R13 | Medium | The long-term service/crate structure could be built before proving one useful result | Add B0–B5 bootstrap sequence, local CLI first, minimal workspace and measured introduction of durable infrastructure |
| R14 | Medium | The handoff carried an unrelated project's planning machinery | Replace paths, prose, manifests, validators and handoff with project-specific equivalents; scan all delivered names and contents for the disallowed marker |

All findings above are addressed in the design. Their implementation tests are planned, not passed. Source pins and original input identity remain distinct; a source map is never automatically labelled verified.

## Sound controls retained

The original executable remains the behavioural reference, with Bosman as a qualified native execution platform. Quick-result and detailed-match evidence remain separate. RNG state/call order/layout are explicit. Traces are bounded and tested for neutrality. Candidate claims and accepted contracts are separate. Rust owns all game rules, and the native/browser builds share the core. Optional features persist versioned profiles without changing faithful-mode expectations. Worker recovery, retention and provenance already had useful boundaries and remain part of the plan.

## Material assumptions still requiring experiments

| Assumption | Earliest experiment | Failure response |
|---|---|---|
| Supplied files match the chosen original baseline | Hash/clean-manifest qualification in P00/P01 | Reject mismatched inputs; register a separate baseline if deliberately supported |
| Bosman is suitable for bulk faithful observations | P02 original/Bosman A/A and A/B cases, hook audit | Classify affected paths; use original capture there; no unqualified Bosman truth claim |
| Relevant state and dependencies can be captured | B2 routine/journey snapshot and restored replay | Expand capture or choose a smaller valid slice; unknown imports stay unsupported |
| Numeric/layout effects can be represented safely in Rust | RNG/numeric/allocator-sensitive cases | Introduce narrow compatibility semantics or record an explicit fidelity tradeoff |
| A Rust feature can be integrated coherently | B3 stateful squad workflow, save/reload and original-backed comparison | Rework dependency boundary before broad porting |
| Representative worlds fit browser resources | P04 large-state memory/storage/import prototype | Measure and reduce avoidable copies/layout cost; make scope/hosting changes explicit |
| VPS capacity sustains useful research | Single worker pilot then measured concurrency | Adjust admission/retention; no speculative server purchase needed |
| Jev improves this specialist workflow | P03 shadow/held-out trial | Keep deterministic/manual triage; Rust development continues |
| Research is reviewable at generated volume | Pending age and accepted findings/reviewer-hour | Throttle candidate generation and prioritise high-value reproductions |
| Whole original feature set is known | P00 direct observation plus continuing coverage audit | Add missing rows/scenarios; no completeness claim while unclassified features remain |

## Definition of ready to start

B0 map import and scope work can start from the pinned public sources. B1 original-game execution needs local input paths and a qualified toolchain. VPS deployment additionally needs host facts/access and bounded storage/backup choices. Broad reconstruction proceeds only where B2 captures valid reproducible evidence. Neither Jev credentials nor a polished dashboard blocks the first Rust slice.

## Verification of this review

The bundle checker verifies exact overlay membership and hashes, canonical paths, phase/dependency agreement and document links. A clean application rehearsal verifies the resulting committed documentation. Negative tests exercise stale bases, omitted/changed files, malformed paths and dependency cycles. These validate the handoff, not the game.

The corrected deliverable replaces the earlier roadmap bundle. No simulator was implemented, no original game was run, and no VPS or model account was accessed during this review.
