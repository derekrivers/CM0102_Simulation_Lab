# Connected effective-plan lookup: frozen R7 qualification

Status: original qualification and exact projection admission passed; production integration under review. Existing v1–v4
contracts and evidence are immutable. New production work requires this original
qualification and independent admission of each exact new projection.

## Supported state and interface

Use only the official PE and existing retained/fresh captures already pinned by
R4 and the option-2 producer. The initialized reciprocal ordinary-club/human
manager binding, registry lifetime, guard DWORD, all mapping rows and all ordinary
bank contents are immutable. Selected human slot and option-2 byte alone are
mutable, exclusively through original commands. No code/guard patch or stub.

Both raw captures contain all fallback dependencies: first and second banks have
17 and 28 slots of 6,371 bytes; the human club mapping row is 145 bytes with signed
16-bit selected plan 0. The full banks and mapping row are present in each. Actual
fallback therefore returns first bank slot 0. Second-bank arithmetic exists in
original code but is not dynamically qualified for these human inputs. Human
registry slots remain a separate location type with 7,885-byte stride.

Proposed fixture schema 3 is exactly `{schema_version:3,registry,ordinary}`.
`registry` is the unchanged schema-2 wrapper and must pass existing inner and
whole-wrapper admission. `ordinary` has exactly `first_bank_count`,
`second_bank_count`, `selected_plan`, `mapping_row_sha256`, `first_bank_sha256`,
`second_bank_sha256`. Hash the full 145-byte mapping row and complete banks;
canonical sorted compact JSON defines the whole-projection fingerprint. The two
real fingerprints require independent raw extraction and approval. These hashes
are provenance, never substitutes for checking original complete captured memory.

Proposed additive Rust world/save v5: `import_effective_reference` accepts a fixture
string; `effective_plan_command` uses the existing session/command/revision/club
envelope plus signed `slot` 0/1. Existing `human_command` and
`registry_option_command` operate within the same v5 revision, event and command-ID
history. One accepted command creates one event/revision even if its original
branch writes nothing; exact retry returns the prior result with no new effects.
Changed retries and invalid actions/imports/replays reject atomically. Preserve
v1–v4 exact bytes/semantics; no migration. Rendering reads state without executing
lookup. UI must explicitly invoke the command and show returned location kind
and branch. Neutral names make no gameplay or match claim.

`EffectivePlanLookedUp` contains requested slot, prior/current selected slot,
option byte, branch, tagged returned location and ordered writes. Branches are
`ordinary_fallback`, `registry_guard_zero`, `registry_option_enabled`. Location is
`ordinary_bank` (bank first, index 0, byte_offset 0 for admitted real inputs) or
`human_registry` (registry index, slot, byte_offset slot*7885). Lookup does not
change the ordinary mapping. Direct selector continues to return its human slot
independently of the later effective lookup result.

## Original entry, reads, branches and effects

`00896660`: ECX is actual captured context; stack arguments are actual nonnull
ordinary club pointer and slot 0/1. Returns EAX location and removes 8 argument
bytes; EBX/ESI/EDI/EBP preserved. Its admitted graph is `00600a50` classifier
(called with club,1,1,0,0), `0053b900`, `005fd210` guard getter,
`005fea50(2,manager)` option getter, `005fbe20` selector with `005409b0` and
`0053b900` classifiers, and `005fbd00` resolver. The standalone producer remains
`005feb60(2,value,manager)`, value 0/1, ret12; direct selector ret12, resolver ret4.
Their incidental EAX values retain existing exact assertions.

Non-stack reads use exact field and width admission: staff/club/nation global
counts and registry object global (DWORD); actual club ID and manager pointer
+0xcf (DWORD); manager ID (DWORD); registry base/count (DWORD); row guard +0x9a01
(DWORD); option +0x9b25 and selected slot +0x9a69 (BYTE); context mapping pointer
+0x601, first-bank count +0x5fd and bank pointer +0x5f9 (DWORD); human mapping
selection (signed WORD). Context second bank pointer +0x5f1 is inventoried but
not admitted in this real first-bank campaign. Raw plan contents are hashed and
preserved, not decoded or read by lookup itself.

Retained actual guard/option/slot is 1/0/0; fresh is 0/0/0. Guard zero takes
registry path without reading option. Nonzero guard reads option: zero returns
ordinary fallback without a non-stack write and leaves selected slot unchanged;
one invokes the selector/resolver, writing exactly one BYTE +0x9a69 and returning
that human slot. Repeated registry lookup still writes. Producer writes exactly
one BYTE +0x9b25, preserving slot/guard; direct selector writes +0x9a69 preserving
option/guard. All other captured bytes and complete loaded official image must
match after every accepted call. No original RNG/system call is admitted.

## Bounded experiment and acceptance

One campaign per retained/fresh input, serial, at most 60 successful original
calls per input, 3,000 instructions and 100ms emulator deadline per call. Full
state comparison after each step, exact original instruction starts, every ordered
non-stack read/write with instruction address, ABI/EAX checks and source/range
hashes. A sequence covers both lookup options, repeats, producer enable/disable,
direct selection before lookup, and mixed complete-captured-memory checkpoint
continuation run twice. Returned pointer is normalized only after exact private
EAX comparison. No expected output is rewritten from emulator output.

Discriminating defects: wrong branch, guard ignored, option ignored, fallback
selection mutation/write, omitted/repeated/wrong-width/wrong-row write, wrong
human stride, wrong ordinary index, reordered mixed effects, extra RNG and
producer/selector cross-mutation. Negative host values are pre-invocation
validation, not original diagnostic parity. Original null-club and unsupported
slot probes stop at their first unqualified boundary and retain ordered partial
effects; never count a censored probe as qualified. Diagnostics expose original
instruction address, field/region category, access width only; no pointer/raw
name/byte dump. All attempts use exclusive private output paths.

Independent review must approve exact source revision before heavy execution,
independently extract the two canonical projections, then review original
receipts and final Rust/browser implementation. Native/WASM equality, v1–v4
compatibility, mixed retries, replay rejection, deterministic save continuation
and actual durable browser recovery remain implementation acceptance, not claims
of this qualifier. Full lifecycle, arbitrary managers/mappings/banks, other
slots/options, original UI/process/save and match effects remain unsupported.

## Original execution and independent admission

Independent R8 reviewer approved exact source `0e6e428` before execution after
requesting exercised defect candidates and complete sanitized failure context.
Two first-attempt campaigns completed, each 33 successful original calls. The
[retained receipt](evidence/pc-r7-retained-effective-plan-v1.json) and
[fresh receipt](evidence/pc-r7-fresh-effective-plan-v1.json) bind source/dependency
hashes, complete input identities, exact starts/ordered effects, ABI, complete
state/image and mixed deterministic continuation. Unsupported probes remain
explicitly not comparable, including retained unsupported slot returning through
fallback without a selector. Fresh-only or retained-only controls are null where
that real capture cannot discriminate the opposite branch. No attempt failed.

Retained receipt SHA256 is `15d7bcd7c0393ef159b9fd62878bee139edaf835958c03fd1d249843c2862e74`;
fresh is `36274441659bf1529466d1eaf35e3a51063ef5387c90d71d16bd63a718064618`.
Fresh command tool wall time was 1.698 seconds. The retained command exceeded
the first 10-second tool yield; precise total host duration was not recorded.
This timing omission does not change per-call emulator bounds or correctness
comparisons and is not represented as a measured total.

The [independent admission](evidence/pc-r7-fixture-admission-v1.json) records the
coordinator's standalone raw extraction, with zero repository parser imports:
exact reciprocal binding, previous schema-2 admission, full mapping row and both
banks, canonical 911-byte real wrappers. Only those two fingerprints and the
independently checked 898-byte synthetic wrapper are admitted. Public files
contain structural counts/hashes only; raw projections and source records remain
private. Profile is `<origin>-effective-plan-v1`; session is
`<origin>-effective-session-v1`. Query response `effective_plan_result` is the
last historical `EffectivePlanLookedUp` event or null, never an implicit lookup.

## Rust integration checks

Core revision `04dd3d7` adds explicit v5 state/history/save and dispatch, leaving
all existing v1–v4 modules and serialized response fields unchanged. Six new
behavioral tests compare original retained connected cases and exercise three-way
retry conflicts, pure queries, no-write fallback revisions, repeats, atomic domain
and fingerprint rejection, resealed history/state corruption, capacity and exact
v1–v5 roundtrips/continuation. The private-world compile-fail boundary is tested.

`cargo test -p cm-management -- --test-threads=1` passes 31 tests (27 behavioral,
4 compile-fail); `cargo clippy -p cm-management --all-targets -- -D warnings`,
`cargo build -p cm-management --bin management-corpus`, release WASM build and
`cargo fmt --all --check` pass. The first test/build attempt passed without a
runtime correction. These are targeted core checks; actual WASM/browser execution,
workspace-wide checks, durable recovery and final independent review are separate
integration gates and are not inferred from a WASM build.

## Integrated native, actual WASM and durable browser result

[Browser acceptance](evidence/pc-r7-browser-v1.json) passes 552 native/Chromium
operations: all prior 375 canonical results remain unchanged, plus 59 operations
for each of three v5 fixtures. Both real captures and the labeled synthetic
fixture execute original connected cases, all three mixed commands/retries,
atomic invalid action/import/replay controls, exact v1-v5 roundtrips and
continuation. React explicitly invokes lookup and displays its actual tagged
return/branch, labels the result historical after later commands, and keeps
rendering/control selection/state queries pure. Capability removal is tested.

[Persistent acceptance](evidence/pc-r7-storage-v1.json) closes/reopens actual
Chromium for twelve profiles, preserving all nine previous profile results.
It verifies no-write fallback publication, full v5 history/retry continuation,
corrupt-current fallback, visible real transaction abort with accepted memory
retained, and delayed/stale same-profile retained/fresh fencing. Both additional
invalid-head cases pass under the unchanged R6 semantics. API-injected
denial/quota and physical-storage limitations remain separate.

The [integrated validation record](evidence/pc-r7-integrated-validation-v1.json)
seals commands, exact source/artifacts/tools/logs and durations. All 86 workspace
Rust tests pass serially, fmt and denied-warning workspace Clippy pass, native
and release WASM builds pass, and strict TypeScript/build pass. An initial
unchanged supervisor timing assertion failed; its log is retained. Isolated
process tests and the full serial rerun passed with no source/threshold changes.
Browser and storage suites ran sequentially in 18.21 and 19.01 seconds. Final
exact-head review and protected-check/merge identities belong to the delivery
record; these gates do not qualify other managers, mappings, lifecycle or matches.
