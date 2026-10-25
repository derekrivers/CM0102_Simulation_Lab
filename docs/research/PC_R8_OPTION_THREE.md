# R8 option-3 dependency boundary

Frozen 25 October 2026 before execution. Research only; no production admission
or UI capability follows from this contract. Existing producer scripts/receipts
remain unchanged. Official PE and retained/fresh inputs retain their prior pins.

## Bounded experiment

At most eight original calls: strict and connected admission, each retained/fresh
and value 0/1. Each starts from immutable captured state; no patched flags, code,
stubs or synthetic binding. Each is limited to 3,000 instructions and 100ms of
Unicorn execution. Stop at the first unadmitted read, write, instruction or call.
No additional dependency is admitted in this campaign. Full captured bytes and
loaded official image are checked after every call, including censored calls,
then restored. Input files are never written. Failed attempts remain retained.

Strict admission permits only option-2 producer fields and the option-3 byte
write at row +0x9b26. Connected admission adds exactly reciprocal manager +0x39
DWORD and existing R4 outer-getter read/instruction inventory (with its actual
selector write, if reached). It stops before 008968f0 entry. Value zero is expected
to return without reading manager +0x39; this is a distinct branch, not evidence
for value one. A completed branch checks ABI/return and ordered effects. Neither
censored call has a full return/ABI or complete RNG claim. Preserve every partial
write, including the initial store even when later execution censors.

Public diagnostics contain original PC, decoded instruction with register/field
offsets, access width, field/region category, and ordered normalized effects.
Never publish native pointers, record contents, names or instruction bytes.
Controls discriminate loss of partial writes, wrong read width/field/PC,
wrong instruction, missing selector write, and falsely marking censored return.
Every call starts from the complete immutable checkpoint. Identical value-zero
paths across admission modes are an admission-invariance check; no deterministic
continuation claim is made for either value.

## Static dependency inventory

005fec19 stores the argument low byte at row +0x9b26. Value zero branches directly
to RET 12; nonzero reaches 005fec2e `mov eax, dword ptr [edx + 0x39]`.
This is the reciprocal manager-to-club DWORD, already captured by both inputs.
005fec42 calls 00896660(club,0), the shared R7 effective-plan path. Its retained
guard 1/option2 0 follows ordinary-bank fallback; fresh guard 0 selects human slot
zero and performs the actual selector byte write. Human slots have stride 7885,
ordinary bank slots 6371. Neither location type can substitute for the other.

The subsequent 16-iteration loop calls 008968f0(club,index,0) at 005fec69.
Static inspection shows mapping DWORD slots at row +2+4*index, staff-table
lookups, staff +0x61 pointer tests, possible mapping cleanup writes of -1,
and classifier 0053b900. Alternate branches consult staff +0x24 and club +0x53.
Thus captured presence alone does not qualify the read/write/lifetime domain.
A nonnull result supplies a staff-ID DWORD stored to registry +0x9b28+8*index.
For indices 0..10, 005b2ae0(plan,index,0) reads a signed 16-bit plan field at
+0x12d+2*index and its sign extension is stored at +0x9b2c+8*index. Indices
11..15 store -1 there. A null result stores -1 in both DWORDs. These effects
are static dependencies, not claimed executed observations. No x87 or RNG call
appears in these immediate normal branches; transitive qualification is open.

## Tractability and stop condition

The first dependency is present, but a complete nonzero path requires staff
mapping validation, possible cleanup mutation, staff-linked object lifetimes and
all loop iterations. R5 captures full staff/mapping/banks but not arbitrary
objects reached through staff pointers. No capture expansion is authorized here.
Stop before the new resolver; report the precise observed boundary and inventory
missing transitive extents. Follow-on estimate: one bounded source/read-set design
and independent review, then a new campaign if every actual extent is captured;
otherwise a separately sealed capture increment. No whole-path date is promised.

## Results

Pending frozen-source review and explicit heavy-slot allocation. Independent
review must assess exact source, diagnostics privacy, evidence and claim scope.

## Separately frozen empty-mapping expansion

Initial campaign source 5928e7d completed its eight calls and remains immutable.
Both value-zero branches returned with exact ABI/effects. Strict nonzero probes
censored at the manager-to-club DWORD, connected probes at 008968f0. Full captured
state/image matched every partial effect; fresh connected calls also wrote the
selected-slot byte. This is a preserved first campaign, not a failed qualification
silently replaced by the expansion below.

Static actual-input inspection found all sixteen mapping DWORDs equal -1 in both
captures. Thus this exact initialized branch needs no staff-linked dereference or
plan-word read. The follow-on budget is four additional calls per source only:
1,1,0, then restore the full checkpoint after the first 1 and execute 1 again.
Compare the repeated suffix result and complete captured state byte for byte.
Each call retains the original 3,000 instruction/100ms ceiling. No retries or
additional branches are authorized. Preserve failures with partial effects.

New source qualify_option_three_empty_mapping.py adds only original ranges
008968f0..00896a8e and 008982b0..008983ed plus exact sixteen mapping DWORD fields.
Every CALL is checked by exact caller PC and target. The resolver's flag-zero
008982b0 branch calls 00600a50 and returns the ordinary club ID; each empty
mapping slot makes 008968f0 return zero before staff or plan accesses. Expected
nonzero return is EAX=ffffffff with RET12 and callee-saved registers preserved.
Writes are the initial +9b26 byte, fresh-only +9a69 selector byte, then 32 DWORD
ffffffff writes at +9b28+8*i and +9b2c+8*i, i=0..15. Value zero only writes +9b26;
it preserves previous loop fields. Full captured/image comparison admits exactly
these byte effects. All other state, including guard/option2/mapping, is immutable.
Mutated effect/width/value/offset/order/RNG/ABI candidates must fail the same
verifier used on observations. No production admission follows. Nonempty slots,
staff-linked lifetimes, plan numeric branches and broader options remain excluded.

Pending independent source review and heavy-slot allocation for this expansion.

The expansion writes separate exclusive `.timing.json` sidecars with measured
per-call emulation and overall host-generation elapsed durations. Timing is host
instrumentation, never deterministic game state or part of the equality verdict.
Unexpected failures retain decoded instruction, PC, admitted reads and every
ordered partial effect. All private attempt files remain preserved.

## Initial campaign receipt identities

Executed source 5928e7d, Python optimized mode, Unicorn 2.1.4/Capstone 5.0.7:

| Input | Calls | Host elapsed | Sanitized receipt SHA-256 |
| --- | ---: | ---: | --- |
| Retained | 4 | 4.67 s | `04a20da3250238a1b7e2d2664d4c28d855c2889f634a17870d341afe85bd2f23` |
| Fresh | 4 | 0.76 s | `97e036f3c8405949e00c9ea9deb506d7bff92581464341f94d2a2bb88719838a` |

Receipts: [retained](evidence/pc-r8-option3-retained-boundary-v1.json) and
[fresh](evidence/pc-r8-option3-fresh-boundary-v1.json). All four value-zero calls
returned; all four value-one calls censored at their frozen boundaries. Failed
harness attempts: zero. Each receipt seals the unchanged imported source files,
Python/module hashes, official specimen and existing capture identities.
