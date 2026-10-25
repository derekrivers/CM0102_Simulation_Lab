# Human tactical registry: bounded command contract

Frozen before implementation on 25 October 2026. This extends the earlier
[manager-bound research](MANAGER_BOUND_PLAN.md). The command is a direct original
API transition over one real, preinitialized human registry record, not a
reconstructed original UI action, holiday command or match effect.

## Original identity and supported state

Use the official PE32 SHA-256
`0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86`.
Reversal pin remains `9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345`.
The retained private image/heap and source-capture identity are the exact inputs
in [the capture receipt](evidence/pc-r3-club-capture-v1.json). Its historical
instrumented Bosman platform and absent contemporaneous consumption seal remain
explicit. No original process is launched. Bosman inventory names guided address
inspection only; no GPL implementation is copied.

The input has one ordinary club with reciprocal club `+0xcf` / staff `+0x39`
binding and a reserved manager ID. Staff IDs equal table indices. The registry
object at global `00b63c98` contains a base pointer and count at offsets 0 and 4.
The actual count is sixteen. Manager index is `staff_id - staff_count + 16`;
full registry rows have stride `0xa6ef`. The input has five complete `0x1ecd`
(7,885-byte) tactical slots per record and a selected-slot byte at `+0x9a69`.
The projected fixture contains counts, stable IDs, slot/index, input identities
and the full registry-row hash. Proprietary contents/names/pointers remain private.

Registry construction is statically corroborated, not replay-qualified:
`005fb549..005fb5a1` allocates sixteen rows with stride `0xa6ef`;
`005fb63a..005fb656` calls reset `005fb810` on reserved staff rows;
`005fb93e..005fb9c9` initializes five slots with a 7,885-byte stride;
`005fbb91` initializes the selection byte. Full constructors include allocation,
OS/CD checks and other dependencies. Construction/load/destruction, appointments,
record reuse and mutable binding/lifetime transitions are outside the command.
The immutable pinned snapshot supplies the required initialized lifetime.

## Direct supported command

`SelectHumanSlot` takes the existing session/command/revision envelope, club ID
and signed slot 0 or 1. It executes the semantics of original
`005fbe20(slot, club, manager)` followed by `005fbd00(manager)` with the actual
registry receiver. All arguments are explicit and nonnull. Ordinary club IDs
must be below `club_count - 2*nation_count`; national/alternate categories are
excluded. Both classifiers `005409b0` and `0053b900` execute original instructions.

Exactly one byte is written, at that manager row's `+0x9a69`, with value 0/1.
Repeating the selected value still emits the write. The resolver returns
`registry_base + manager_index*0xa6ef + slot*7885` and writes nothing. No RNG
routine or unadmitted instruction/read/write may execute. Do not model this as
a pure getter and do not reuse the 6,371-byte ordinary-bank `PlanLocation`.
Rust emits `HumanSlotSelected`, including old/new slot and the ordered byte
write. Revision/events/deduplication are the new host protocol, not observations
of an original event system. Unsupported slot/club/session/revision/identity,
changed retries and malformed saves reject before mutation.

## Outer getter and state producer

The actual captured record has `+0x9a01 == 1` and `+0x9b25 == 0`. Original
`00896660` classifies it as human but follows the ordinary-bank fallback after
`005fd210` and `005fea50(2,manager)`. The direct selector command does not claim
to change which plan that outer getter uses under these captured flags.

The precise producer of the second guard is original
`005feb60(option,value,manager)`: instruction `005fec19` stores the low byte at
`row + 0x9b23 + sign_extend(option)`. Option 2 returns without the extra option-3
lineup dependencies. The oracle executes `(2,1,manager)` entry-to-return, then
runs `00896660` with options 0/1. That connected path calls both selector and
resolver, writes the same selection byte, and returns the same slot pointer.
A final original `(2,0,manager)` restores the observed guard. These are explicit
research probes, not a newly exposed holiday-setting command. Option 3 and
other unsupported producers stay censored; no guard is patched to manufacture
successful execution.

## Acceptance and compatibility

The original oracle checks full captured heap and loaded image after supported
steps, every ordered non-stack write, instruction/read admission, stack cleanup,
callee-saved registers, return values and deterministic continuation. Negative
controls must discriminate wrong row/slot/stride, omitted/wrong-width/reordered
writes and additional RNG consumption. Unsupported original paths retain their
censoring boundary; Rust host rejection is not original diagnostic parity.

Production admission requires exact reviewed real/synthetic fingerprints;
synthetic fixtures are labeled separately. Use an explicit version-3 slice
save for this profile, reconstruct and replay its accepted commands, and compare
full state/events/records before committing load. Keep v1/v2 serialization and
semantics unchanged. Actual native/browser execution and recovery must compare
exactly. React exposes the new command only for an admitted human fixture and
uses neutral research slot labels. R5 captures require their own structural
qualification and cannot self-admit by presenting a new fingerprint.

## Reproduction

`python3 scripts/qualify_human_registry.py /private/official/cm0102.exe
/private/retained/snapshot /private/new-receipt.json
--private-fixture /private/new-fixture.json`

Requires Unicorn 2.1.4; outputs use exclusive creation. Public receipt contains
structural results and hashes only. The private fixture contains stable real
record IDs and stays outside Git/build output. Raw original records, code and
traces must not be redistributed.

## Initial executable results

The [sanitized original receipt](evidence/human-registry-oracle-v1.json) records
21 successful calls over 345 instruction starts, six direct-selector cases,
four connected outer-lookup cases, captured fallback, original guard enable and
restore, and checkpoint continuation. Seven defect models discriminate; three
out-of-domain probes remain censored and not comparable. An optimized-Python
rerun reproduced receipt SHA-256
`39f483c2d181b76fc44b4319bc924878cce125838a0ddc013dffe0525a780438`.

The additive `human` module admits exact real/private and synthetic identities.
Version 3 has its own fixture, selected byte, ordered effects and replay records;
legacy worlds are not reserialized through a new schema. Six new Rust tests
cover oracle effects, rejection, checksum-repaired corruption, continuation,
profile switching and the 256-command boundary. All thirteen management behavior
tests and two invariant compile-fail checks pass; fmt, denied-warning Clippy and
native/WASM builds pass. Four Python structural/identity controls pass under
`-O`. The browser corpus helper is ready; actual browser and durable human
profile acceptance still require integration validation and independent review.

Commands: `cargo test -p cm-management`, `cargo clippy -p cm-management
--all-targets -- -D warnings`, `cargo build -p cm-management --bin
management-corpus`, `cargo build -p cm-management --target
wasm32-unknown-unknown --release`, and `python -O scripts/test_human_registry.py`.
One initial build command used nonexistent target `management-native`, failed
without running it, and was corrected to the repository's `management-corpus`.

## Fresh pinned-platform sparse replay

The independently parsed R5 enabled capture contains sixteen sealed regions,
3,849,184 bytes in its complete artifact, SHA-256
`014808018f7b20f60abaac5c71a0c509747259e309563650afe0d0cc79da6f40`.
Its instrumented platform is pinned Bosman
`144ed82c248228c7769c6785899527eae5b33c3d`; the derivative binary hash and build
receipt hash travel in the [fresh oracle receipt](evidence/fresh-human-registry-oracle-v1.json).
Endpoint, A/A, instrumentation comparison and input-consumption limitations remain
R5 campaign claims, separate from this original-instruction replay.

The fresh real human record has guard `+0x9a01 == 0` and `+0x9b25 == 0`.
Consequently the outer getter takes the registry path directly from captured
state, unlike the older retained holiday-state fallback. Twenty-one original
calls cover 290 instruction starts. All declared captured regions and the entire
loaded official image remain unchanged except the precisely allowed bytes;
uncaptured runtime memory is not claimed checked. Each executed non-stack read
is within the explicit supported captured state. Seven defect models and
checkpoint continuation pass; out-of-domain probes remain censored.

The fresh oracle receipt SHA-256 is
`39915e94bf65ca7c6586153dffa63b03160dc483119a58e8dc9e82fbc92fd911`.
Its projected fixture fingerprint
`15697cfbb10725a20c50a8bb290ff8fe85fd05c572d8f7302d4ddbc95e842dc2`
was **not admitted by that oracle or PR #35**. The separate admission review below
now admits this exact projection alongside the retained private fixture; neither
a capture nor an oracle grants itself new production authority. The updated shared oracle reproduced the retained receipt
byte for byte. Five Python controls now include sparse completeness, identity
and overlap checks. No R5 script import is required by the independent parser.

Fresh reproduction: `python -O scripts/qualify_fresh_human_registry.py
/private/official/cm0102.exe /private/enabled-a/capture.bin
014808018f7b20f60abaac5c71a0c509747259e309563650afe0d0cc79da6f40
/private/build-receipt.json /private/new-oracle.json`.

## Integrated browser and recovery result

The [browser receipt](evidence/pc-r4-human-browser-v1.json) retains 159 exact
native/Chromium operations: unchanged 105 legacy/ordinary cases plus 27 each
for the labeled synthetic and real retained human profiles. All six admitted
original selector cases feed each human corpus. Complete state, ordered writes,
events, records, rejections and saves match; v3 reload/deduplication/continuation,
legacy byte-identical v1 exports, capability-gated Apply slot, invalid imports
and reset pass. The private fixture stays outside Git and build output.

The [v3 storage receipt](evidence/pc-r4-storage-v3.json) extends the same R6 host
contract to all five admitted profiles. Actual persistent Chromium process
close/reopen preserves exact Rust save/state/events/deduplication and native
continuation. The existing abort/corruption/interruption/session/tab controls
remain passing; quota/denial API injection and physical-durability limits remain
explicit. No separate mutable TypeScript engine or human storage format exists.

Coordinator independently reproduced both original receipts under optimized
Python: retained 21 calls/345 starts and fresh 21 calls/290 starts are byte
identical to their public receipts. Five Python controls pass. Integrated Rust
checks pass 70 tests (including two compile-fail boundaries), formatting, denied-
warning workspace Clippy, native and WASM builds; strict TypeScript/build checks
pass. Models remain Astra/high research, Sol/medium capture and unchanged
coordinator; independent core/evidence and UI reviews plus final CI/merge are
recorded in the delivery PR. Fresh input admission required the subsequent review below.

## Independently reviewed fresh-fixture admission

On 25 October 2026 an independent Astra/high reviewer who authored neither R4 nor
R5 approved only fingerprint
`15697cfbb10725a20c50a8bb290ff8fe85fd05c572d8f7302d4ddbc95e842dc2`.
The [admission decision](evidence/fresh-human-fixture-admission-v1.json) binds the
existing capture/build/oracle receipts to an independent raw projection: 481
canonical bytes, mode 0600, retained outside Git. The reviewer checked 274 private
artifacts, 264 sealed build objects, source/tool/header/native identities, all
760 clean files, four chronological stable arm seals and exact saves/captures.
Official disassembly and both original-instruction receipts were independently
checked; fresh 21/290 and retained 21/345 reproductions were byte-identical.
Private audit and standalone projection-script identities travel in the decision.

This is one additional exact allowlist entry for the existing captured origin,
direct-human-slot-v1 profile and v3 format. Retained fingerprint `986a2f…` remains
admitted. No migration, session-name change, broader command, outer-getter model,
registry lifecycle or new original-process/clean-consumption claim is introduced.
The original fresh oracle's `not-admitted` field remains an immutable statement
of its authority when generated, superseded only by this separate reviewed decision.

[Browser acceptance](evidence/fresh-human-admission-browser-v1.json) passes 204
exact native/Chromium operations: the prior 159 unchanged, 27 fresh oracle/UI
operations and 18 fresh/retained admission/compatibility controls. The fresh corpus
uses the fresh oracle explicitly. Wrong source/row/specimen/origin/initial-slot,
hybrid identities and checksum-repaired embedded fixtures reject atomically.
Retained and fresh v3 saves each round-trip byte for byte and continue correctly.

[Recovery acceptance](evidence/fresh-human-admission-storage-v1.json) closes and
reopens actual persistent Chromium for all six admitted fixtures. Exact saves,
state/events/records/deduplication and native continuation match; all previous
five storage results are unchanged. Fresh corruption fallback and actual aborted
transaction preserve the prior checkpoint and visibly report accepted unsaved
work. Delayed publication and stale tabs cannot replace a different imported
fixture even when profile and Rust session names match. Existing storage denial,
quota-error, interruption and recovery controls also pass with their established
injection/physical-durability limits unchanged.

Validation passes 71 Rust tests with serial test execution, formatting, denied-
warning workspace Clippy, native/WASM builds and strict TypeScript/build checks.
The initial parallel workspace run failed three unchanged five-second supervisor
timing assertions; the complete serial rerun passed without source/deadline/CI
changes. That failed run is retained in the admission decision. Final independent
exact-head review, frozen CI and merge disposition are recorded in the delivery PR.

Admission merged in [PR #38](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/38),
merge `d1df089e6521113afda787be2d20340c17ea99de`. The independent reviewer
approved exact head `21eed5453282e0904902c626d2a3386450f9fcc1` after reviewing
all changed source/tests/docs and independently passing the 16 management tests.
All four frozen checks passed, including default parallel Rust tests. The
final private review audit identity is recorded in the admission decision.
