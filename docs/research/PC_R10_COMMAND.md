# R10 original lineup command dependency boundary

Status: the retained-only original assignment/readback campaign passes its
frozen dynamic checks; independent post-run review is pending. No production
admission. This does not complete the requested real squad, lineup change,
save/reopen and continuation milestone. R8's already qualified empty option-3
branch remains valid and unchanged; it is not rerun or exposed as a lineup command.

## Pinned original findings

The [static inspector](../../scripts/pc_r10_command_static.py) independently reads
the official PE file, validates its exact 7,192,576-byte identity and PE32 image
base, and checks 41 instruction facts with Capstone 5.0.7. The
[receipt](evidence/pc-r10-command-static-v1.json) seals eight original code ranges
and inspector/decoder identities. It executes zero original instructions. Names
below describe inspected behavior; imported function names are not evidence.

`00896a90` is an actual mapping-assignment candidate. Its receiver is the tactical
context; stack arguments are `(club, index, nonnull staff, row mode)`. The low
byte of index is interpreted as signed, with original bounds 0 through 19. The
routine calls `008982b0(club,row mode)`, computes the mapping row with stride 145,
reads the staff ID DWORD at staff offset zero, and writes it to mapping row
`+2+4*index` at original PC `00896b98`. Success returns EAX 1 with `RET 16`.

A following cache-count BYTE read at context `+0x5f0` makes this more than an
unconditional isolated DWORD setter. When nonzero, the original scans sixteen
records at context `+0x30+0x5c*i`, compares active/club/mode fields, clears matching
active DWORDs, and decrements the count BYTE for each matching entry. No cache
branch is admitted by this static report. Both currently inventoried inputs have
cache count zero; that fact needs independent input verification for any campaign.

`008968f0(club,index,row mode)` is the corresponding nonempty read dependency.
It uses the same 20-slot signed-byte domain and row resolver, reads the mapping
DWORD, and returns zero for values at most -1. For a nonnegative ID it indexes
the staff table with stride 110, tests staff `+0x61` DWORD, and **writes -1 back
to the mapping** if that link is null. Thus it is not generally a pure getter.
For an ordinary club the nonnull path returns the staff record; the linked player
record itself is not dereferenced. National categories additionally inspect staff
`+0x24` and club `+0x53`; those paths are outside the candidate domain.

`008982b0` uses original classifier `00600a50`; row mode zero ultimately returns
the actual club ID. Nonzero row mode can select a separate alternate human row
using manager/count/category state. Only ordinary-club mode zero is proposed;
empty alternate rows or AI mappings cannot substitute for real human input.

Two original excerpts corroborate the input relationship without qualifying
whole calls. `0090d429..0090d45b` counts fifty nonnull DWORD slots beginning at
club `+0xd7`, advancing four bytes. `0076263b..0076267d` recovers a staff record
from its ID, compares its `+0x39` club against the manager's `+0x39` club, and
only then calls `00896a90(club,index,staff,0)`. These are static relationship
checks, not proof that every captured slot is currently eligible or that a
nonnull `+0x61` points to a live player record.

## Exact proposed input and command boundary

The assigned input and independent projection lanes inventory the unchanged
retained complete image/heap and R5 sparse state. Existing initial human standard
mapping has twenty empty DWORDs; sixteen were the earlier R8 domain. No human
mapping is patched or populated from AI state. An original assignment could
produce real nonempty mapping from an independently qualified actual member;
that would be a genuine original transition, not evidence that a preexisting
nonempty mapping was recovered.

Before any such campaign, freeze two actual candidate staff IDs selected from
independently established club membership, complete aligned staff extents and
stable IDs, reciprocal club links, complete linked-player extents/identities and
an immutable captured lifetime. A same-club pointer and nonnull player link alone
do not satisfy this gate. Preserve mismatched membership entries rather than
silently filtering them to claim a complete qualified squad.

The narrow candidate is slot-zero assignment between those two real members,
row mode zero, actual reciprocal ordinary human binding and cache count zero.
Required reads are exact DWORD fields for club ID/+0xcf, manager ID, staff and
club/nation counts, tactical mapping pointer, selected staff ID/+0x61 and selected
mapping DWORD; cache count is a BYTE. Input admission additionally checks member
list, reciprocal +0x39 and complete linked-record identity without treating those
checks as additional original reads. All other captured regions, official image,
registry state, bank contents and mapping entries remain immutable. The selected
mapping DWORD alone is allowed to change under this zero-cache candidate.

No inferred football eligibility, automatic duplicate removal, swap semantics,
position name, rating or original UI-handler claim follows. Original assignment
itself does not remove a duplicate elsewhere; several original callers explicitly
invoke a larger removal routine before assigning. A future public action must
state its supported original domain rather than invent that caller behavior.

## Gates before implementation or execution

The concrete candidate IDs/source hashes, full exact instruction/call/read/write
allowlists, return/ABI model and budget must be frozen and independently reviewed
before an emulator campaign. Proposed acceptance includes initial assignment,
repetition, replacement, original readback, complete captured/image comparison
after every call, exact ordered non-stack reads/writes, preserved EBX/ESI/EDI/EBP,
RET16/RET12 and exact EAX, zero RNG, and repeated full-checkpoint continuation.
Defective models must discriminate wrong staff/index/width/row, omitted repeated
writes, readback cleanup, cache mutation, extra RNG and incorrect ABI.
Unsupported original arguments must censor at the first unqualified boundary,
retaining original PC, decoded instruction, width/field and all partial effects;
host rejection is not original diagnostic parity. No experiment is authorized by
this proposed design alone; lead allocation follows exact independent review.

The shared Rust/save/protocol/UI implementation remains a required carry-forward.
No production command, fixture fingerprint, save version or compatibility change
is implemented by this research record. Original process/platform file-use,
full lifecycle and original-save parity remain separate gates.

## Frozen retained-only campaign: 25 October 2026

The executable [qualifier](../../scripts/qualify_pc_r10_command.py) now freezes
one campaign over the exact retained image/heap pins, with no fresh capture or
fresh-input admission. Static original `008b3cdc..008b3d2e` corroborates player
count global `00ae236c`, table global `00ae23c4`, ID DWORD at offset zero and
70-byte iteration. `00526535..0052654d` constructs the same 70-byte table address
and stores it to staff `+0x61`. The whole retained 504,980-byte player table has
7,214 ID/index-matching records; independently inventoried member links land on
complete aligned records. Those facts establish initialized captured identity,
not constructor/load/destructor behavior. The campaign additionally qualifies
only their immutable lifetime across its exact entry-to-return sequences.

The chosen two members are the first two by ascending staff ID among the 43
aligned, ID-correct, reciprocal club-list candidates with complete, aligned,
ID-correct player links. All 48 aligned list pointers are checked; two invalid
entries and five reciprocal mismatches are counted and remain unqualified.
Exact real IDs and records remain private. Per-record hashes and player-table
identity bind this deterministic selection. No membership anomaly is repaired.

Read admission is exact field and width. Assignment reads club/manager/count
classifier state, club ID, context mapping pointer, the chosen staff ID and cache
BYTE. Readback additionally reads mapping slot zero, staff-table global and the
chosen staff player-link DWORD; it never dereferences the player link. Candidate
ID/link fields for only the two chosen members are admitted. The class implements
a shared union of these field allowlists, while every call separately records
its ordered PCs/fields/widths; the complete checkpoint suffix must repeat those
reads and instruction starts exactly. Ordinary classifier thresholds use the
actual club/nation counts. All five code ranges and five permitted CALL edges are
frozen in the qualifier. Before execution, a complete linear Capstone decode of
those exact original ranges freezes valid instruction start/size pairs; the hook
rejects entry into any other byte boundary. Diagnostic CALLs stop before entering their callees.

Eleven successful calls are planned: initial empty readback; assignment/readback
for candidate 0, repeated candidate 0 and candidate 1; then candidate 0 plus
readback twice from the same complete post-candidate-1 checkpoint. Each assignment
must write one DWORD at PC `00896b98`, including repeats, and return exactly 1
with RET16. Each readback writes nothing and returns zero initially or the exact
private chosen staff pointer with RET12. Original code must preserve EBX, ESI,
EDI and EBP. Expected full heap is constructed from immutable captured bytes plus
only the selected mapping DWORD; every byte and the loaded official image are
checked after each call. All declared object bytes and link values are thereby
held invariant for this exact initialized lifetime. No RNG/system/unadmitted
callee is allowed.

Four additional original probes (null club, signed index -1, index 20, null staff)
start independently from the complete final checkpoint and must censor at
`00896abd`, `00896c06`, `00896c06` and `00896b12` respectively, preserving all
partial effects and full state. These are unavailable original diagnostics, not
successful rejection parity. Host slot 1/256 and candidate out-of-domain rejection is not
tested here because no production validator exists. Twelve exercised defective-model
controls cover player/slot/width/write omission/cache mutation/PC/RNG/return/ABI,
immutable state digest corruption and erroneous readback cleanup/return.

The total ceiling is 15 original calls, each at most 3,000 instructions and
100 ms emulator time, under an outer 90-second wall limit, 60-second CPU limit,
1 GiB address-space limit, 16 MiB per output file and 1 MiB captured console limit.
The inspector is separate static work. No retries are included: any unexpected
boundary or mismatch retains its receipt/timing sidecar and requires a separately
reviewed diagnosis and budget. Source/tool/input hashes and actual host/per-call
durations travel with the result. Exclusive new private paths prevent overwrite.
Independent source/contract review and the lead's heavy-slot allocation are
required before execution. No campaign has executed at this freeze.

## Retained initialization failure and separately frozen follow-up

The independently approved exact source `320b9ba` ran once under the original
1 GiB address-space ceiling. It failed before its first original call: Unicorn's
native library could not allocate its translator buffer and exited 1. The outer
launcher retained empty stdout, the allocator diagnostic, exact source/input/tool
seals, command/limits and elapsed 0.549156385 seconds. No Python oracle receipt or
timing sidecar could be completed after that native exit; the outer result is the
failure evidence. No original mapping write or instruction execution occurred.
The [initialization record](evidence/pc-r10-command-initialization-v1.json) preserves
this failed attempt unchanged; it is not counted as a successful campaign.

Three isolated zero-game initialization controls then instantiated the installed
Unicorn 2.1.4, queried its native translator size and mapped one empty page; no game
input was loaded and no instruction executed. The 1 GiB case reproduced exit 1;
2 GiB and 3 GiB cases succeeded and reported an unchanged default translator
reservation of exactly 1,073,741,824 bytes. Successful minimal initialization used
1,092,032 KiB virtual address space, already exceeding the failed ceiling, while
resident memory stayed below 26 MiB. The installed Python control API and retained
logs are hashed in the initialization record.

The new follow-up budget is **one** additional retained-only campaign, maximum
15 original calls, with address-space ceiling **3 GiB**. This accommodates the
observed 1 GiB virtual translator reservation plus full 108,564,672-byte captured
heap, mapped heap, checkpoints and exact comparison buffers. It does not change
the installed translator configuration, qualifier instructions, candidate data,
original writes, comparisons, or per-call bounds. Outer limits remain 90 seconds
wall, 60 seconds CPU, 16 MiB per output file and 1 MiB per console stream. The
qualifier source remains exactly that independently approved at `320b9ba`.

A new exclusive attempt directory and freshly sealed outer launcher are required.
Independent review must approve this diagnosis/resource delta before the lead
allocates a new heavy slot. No unreviewed retry is authorized and no further
retry follows from this follow-up freeze. The old attempt and its original limit
remain immutable. Execution and production admission remain pending.

## Executed retained original assignment result

The separately reviewed follow-up completed at exact source `f6b4052`, with the
qualifier unchanged from `320b9ba`. The [original receipt](evidence/pc-r10-command-retained-oracle-v1.json)
SHA-256 is `504f4f1142597f4f8e451e15837383df2527a2afc921149e4f72d75a8fb8d877`.
The [execution record](evidence/pc-r10-command-execution-v1.json) seals the private
outer launcher, commands/source/tool/input identities, timing, logs and result.
Outer elapsed time was 13.849964520 seconds, exit 0, without a triggered limit;
all before/after source, official PE, raw snapshot and tool seals match.

Eleven original calls return successfully: five assignments and six readbacks,
including initial empty readback. Each assignment executes 123 original
instructions and exactly one DWORD store at `00896b98`, including repeats. Each
nonempty readback executes 152 instructions, returns the exact selected staff
pointer and writes nothing; initial empty readback executes 120 instructions.
The assignment from initial -1 to the first member, repetition, replacement by
the second member and restoration to the first all match their predeclared
semantics. This genuinely creates nonempty mapping through the original entry;
it does not retroactively establish a preexisting nonempty human input.

Every call checks all 108,564,672 captured heap bytes and the complete loaded
official image, exact EAX/stack cleanup/callee-saved registers, ordered admitted
reads and non-stack writes. Full staff/player/member-link/table bytes remain
unchanged through the sequence. Both exact selected record pairs match the two
independent raw extractions. This qualifies only the two initialized captured
object lifetimes across this bounded sequence; no constructor, appointment,
load/free or other lifecycle transition executes or is admitted.

The full checkpoint suffix matches complete heap/image, ordered reads, instruction
starts, effects and returned results exactly when repeated. Twelve defective
model candidates are rejected. The four unsupported original calls censor at
their frozen diagnostic-call PCs, with decoded instruction and empty partial
write sets retained; their original diagnostics were not executed. No host-domain
rejection or production-validator parity is claimed.

The first native initialization failure remains in the denominator as one failed
attempt with zero original calls, followed by this separately reviewed successful
attempt. The default translator was not changed. No further original campaign
ran or is authorized by this result. Private object IDs/bytes/pointers remain
outside Git; public results normalize the two actual records to candidate 0/1.

## Required implementation carry-forward

The lead can use the original-backed transition **assign one of these two exact
admitted members to mapping slot zero, then return original readback**, with the
strict ordinary-mode/zero-cache/immutable-binding domain above. A repeated
assignment still records its original write. Atomic host rejection, command-ID
history, serialization/replay and browser storage are new Rust/host requirements,
not original event/save behavior observed by this qualifier.

This lane does not admit a whole-squad projection or a production fingerprint.
The seven anomalous fifty-slot entries remain unresolved, the fresh sparse input
lacks required player extents, and no original duplicate-removal/swap/position
semantics are qualified. Rust command integration, independently admitted squad
projection, explicit save/profile compatibility, the actual browser journey and
native/WASM persistent save/reopen/continuation remain required work. This
research increment alone does not complete the player-visible milestone.
