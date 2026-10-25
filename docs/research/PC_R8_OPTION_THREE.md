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
