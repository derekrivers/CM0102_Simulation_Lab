# Max Evans upstream integration

These two projects are foundations of CM0102 Simulation Lab:

| Project | Selected source pin from this planning audit | Role |
|---|---|---|
| [cm0102-bosman-edition](https://github.com/maxevans60/cm0102-bosman-edition) | `144ed82c248228c7769c6785899527eae5b33c3d` | Native game execution, translated-code instrumentation, runtime and reusable tests |
| [cm0102-function-map](https://github.com/maxevans60/cm0102-function-map) | `2bb558ef6a6bcdbd304dd1a6a4cf156c6707007c` | Existing functions/globals inventory, names, confidence and evidence links |

The pins are audited snapshots, not claims about the latest release. The inspected Bosman README includes a forthcoming-release placeholder; use the commit, not a presumed release label. Original 3.9.68 executable/data hashes are a separate identity and must be measured from the supplied inputs.

## Integration sequence

1. P00 records repository URL, full commit, licence, input SHA-256 and extraction-tool identity in a future `config/upstream-lock.json`. That file is created during implementation when real hashes are available, not populated with placeholders that might pass validation.
2. Import the map immediately. This read-only work does not require waiting for the game executable or VPS. Retain downloaded TSV bytes and their hashes; publish only material permitted by its terms with attribution.
3. Build Bosman from its pinned source in a separate checkout/build area with private original inputs. Record toolchain, source changes, generated output and binary digest. Keep the main project Rust-first; do not rewrite the recompiler as a prerequisite.
4. Run the applicable upstream tests and retain outcomes, including skips and platform constraints. Establish a reproducible single-worker run before adding the queue or more workers.
5. Add the Rust process adapter and narrowly scoped instrumentation. Connect runtime observations to original-address identities already in the imported map.
6. Compare selected original execution against Bosman. Add Rust as a replacement backend slice by slice, with evidence provenance maintained across all three.

## Bosman build contract

The inspected [build instructions](https://github.com/maxevans60/cm0102-bosman-edition/blob/144ed82c248228c7769c6785899527eae5b33c3d/README.md) take the original release ISO and official patch through `tools/clean_files/make_clean_files.py`; that checks the clean-file manifest. Dependencies include Python/Capstone, CMake, a C compiler, SDL2, bsdtar and unshield. A qualified adapter may accept an already extracted installation only after validating the required files against the selected baseline. Never silently accept a patched executable.

Record CMake options and actual build commands/results in the attempt/build manifest. Compilation parallelism uses measured memory limits, not a copied fixed job count. Generated C is a build product; its original-address correspondence is useful for instrumentation but it is not recovered high-level original source.

The runtime and scripts assume particular data/layout/configuration. Inventory feature hooks, settings, save behaviour and test-only changes. Baseline requests use the matching 2001 data and changing-rules off, then verify observed behaviour; a flag is not a universal guarantee of original fidelity.

## Test reuse and adaptation

| Upstream entry point | Reuse in our lab | Qualification |
|---|---|---|
| `tests/seasons/full_play_run.py` | Detailed-engine-enabled holiday campaigns and periodic saves | Adapt Mac-specific HOLD/load/process scheduling; verify targeted fixture path |
| `tests/seasons/soak_run.py` | Quick-result world/lifecycle campaigns | Keep result class distinct from detailed match evidence |
| `tests/smoke/smoke_run.py` and same-save scenarios | Startup/player journeys, controlled replay and feature noninterference | Check required fixtures, timing rules and permitted differences before adopting |
| `tests/diff/cases_random.py` | RNG routine/state differential patterns using original code | Preserve table/input identity, full state and floating-point control assumptions |
| `docs/TESTING.md` and applicable CTest targets | Upstream test selection and known pitfalls | Reproduce locally; an upstream reported pass is not our result |
| Season/data/screen reports | Coverage seeds for competition and presentation research | Inventory exact available scripts and output schemas at the pin |

Scripts may inherit environment variables, manipulate HOME for isolation and operate an internal UI loop. Our supervisor owns per-attempt directories, allowlisted environment, timeouts and admission control. Remove only machine-specific orchestration assumptions; record any semantic changes as an adapter patch. Upstream same-save checks may include documented exceptions; audit each before defining our exact comparison policy.

No proprietary save fixture is assumed available merely because a runner references it. Generate a reproducible local fixture or obtain an authorised one, hash it, and record its creation path. Full-game original Windows calibration remains separate from Unicorn micro-routine checks.

## Function/global map ingestion contract

Start with these pinned upstream files:

- `map/function-files.tsv`: broad address inventory including game/runtime/unwind categories and source attribution.
- `map/functions.tsv`: named function records and available metadata.
- `map/names.tsv` and `map/not-high.tsv`: naming provenance and unresolved naming evidence.
- `data-map/globals.tsv` and `data-map/data.tsv`: globals, size/type, names, ownership/read-write relations and confidence metadata.
- Associated Markdown pages: descriptions and cited research context, linked by source location.

The upstream README distinguishes 6,863 named game/library functions from 11,747 total function starts, including runtime/unwind items, and 4,428 globals. These are source-reported catalogue sizes at the audited snapshot, not locally verified behaviours or a reconstruction-completion percentage. Compute actual parsed counts during import and fail unexplained drift; a mismatch is investigated rather than forced to match.

Use header-driven parsers, not positional assumptions. The inspected global header includes address, size, type, name, readers, writers, confidence, model and cited_in; the broad function inventory includes address, category, file, method and instructions. Validate each file's actual header and required columns before ingestion. Preserve extra fields for forward compatibility. Every row retains source path, row identity, source hash and import version.

Validate addresses against the original PE image/section map when available; until then mark address validation pending. Preserve VA and derived RVA separately. Register aliases and source categories; keep globals/types separate from functions. Named and broad inventories have different denominators, so reconcile their join and classify missing/duplicate/unmapped entries. Never delete unnamed/runtime entries to improve coverage.

Import updates are idempotent. Store upstream assertions in immutable source revisions; local hypotheses, verified contracts, tests and Rust links form separate records referencing those revisions. New upstream names create aliases/change proposals; they do not overwrite a reviewed local contract. Confidence scales remain source-specific.

## Instrumentation and updates

Prefer a small versioned Bosman patch series over a long-lived unsynchronised fork. Every patch states purpose, touched original addresses, expected overhead, trace schema and A/A neutrality tests. Trace and untraced binary digests are different backends. Private game bytes remain outside Git.

For an upstream upgrade, produce a source/map diff report, inspect changed hooks and schemas, rebuild, run the fixed regression/calibration corpus, compare traces/save semantics and measure overhead. Accept the candidate pin only after review; ongoing campaigns retain their old source identity. If a map source and executable disagree, quarantine affected rows. Never auto-follow upstream main during a campaign.

Record upstream licence and attribution per imported/adapted file; see [technology decisions](../architecture/TECH_STACK.md#provenance-and-distribution). Keeping a dependency external does not itself establish distribution rights. The original executable remains the final reference for faithful behaviour.

## Integration acceptance

P00: both pins registered, map parsed idempotently with reconciled counts and provenance, pending binary checks visible. P01: reproducible Bosman build, actual test report, isolated full/quick jobs and replay artifacts. P02: original/Bosman calibration and trace-neutrality evidence. P03: a trace leads through an original address to imported context, our experiment, a reviewed contract and any Rust implementation link. No unverified integration is described as complete.
