# Fixed registry option-2 producer

Frozen bounded extension of [direct human slot selection](PC_R4_HUMAN_REGISTRY.md).
The official specimen and both existing retained/fresh captures keep their prior
identities and provenance limits. No new original process or Bosman run is needed.

## State and transition contract

Original `005feb60(2,value,manager)` receives the existing registry object and
explicit actual reserved manager. Only values 0/1 are admitted. The supported
path writes one byte at that row's `+0x9b25`, including repeated values, with no
RNG draws. It leaves the selected slot byte `+0x9a69`, immutable DWORD guard at
`+0x9a01`, other rows, plan contents and all other captured state unchanged.
The real retained initial tuple is guard/option/slot `1/0/0`; fresh is `0/0/0`.
The gameplay meaning remains unknown. Option 3 and other indices, null/implicit
manager paths, lifecycle, appointments and original UI handlers remain excluded.

The command does not invoke the outer tactical getter. Its guard-dependent
fallback remains a separate previously observed path, not an implicit effect.
Existing direct slot selection changes only `+0x9a69` with the same slot resolver.
Both commands must preserve the other's state and the initialized binding.

## Explicit compatibility decision

Fixture schema 2 wraps the exact existing admitted human projection as `human`,
plus `guard_9a01:u32` and initial `option_two:u8`. Both guard and option are
restricted to 0/1. Whole-wrapper fingerprints require independent review as well
as inner admission; a caller cannot invent initial bytes or hybrid identities.
Synthetic evidence is separately labeled and cannot qualify real state.

World and slice save version 4 use profile
`<origin>-human-registry-producer-v1`, session
`<origin>-registry-session-v1`. No automatic v3 migration occurs. Existing v1,
v2 and v3 load/export behavior and exact bytes are retained. The new profile
tracks selected slot, option byte and immutable fixture, with one common revision,
event sequence and command ID/retry scope across both commands. Repeated values
are accepted writes; exact retries return the original result without a new write
or revision. Changed retries, including a different command kind with the same
ID, reject atomically. Save loading reconstructs from admitted initial state,
replays all commands and compares the complete state/events/records before commit.

Transport: `import_registry_reference` takes a fixture string;
`registry_option_command` takes the existing session/command/revision/club envelope
and signed `value` 0/1. The option index is fixed and absent from the request.
`human_command` retains its slot envelope and operates within v4's shared history.
Rust owns validation, transition, ordered effects, saves and replay. React shows
neutral research controls only after v4 admission. The existing IndexedDB host
stores the exact Rust save with generic identity and publication fencing.

## Acceptance

New original-instruction receipts must check every entry to return, ABI, reads,
ordered writes, complete captured state/image and mixed checkpoint continuation;
wrong row, byte/width/offset, omitted/reordered effects and RNG models must fail.
Independent raw projection and qualification review precede admission. Native and
actual Chromium must match complete state, effects, errors, saves and continuation.
Recovery must preserve both commands, retries and exact saves through real browser
close/reopen, fallback, transaction abort and stale/delayed writer controls.
All prior corpus and stored-result hashes must remain exact. Final exact-head
independent review and frozen checks precede the authorized merge.

## Independently reviewed admission

An independent reviewer reconstructed both 540-byte real wrappers directly from
the pinned raw states without importing either existing capture parser, checked
the unchanged embedded human identities and observed full DWORD/byte widths,
and inspected the official producer instructions. Approved whole-wrapper hashes:

- Retained: `cc7e3483d1ba7dfd36516f500362f20c63fd23a703f26e9cf20490f0251b616f`.
- Fresh: `e5411188dcb8fe67187930a56c7c224294182bdcef3b684d34d0b8456ee94a5b`.
- Separately labeled synthetic (527 bytes): `f4fd4d0ddea2476728074256bb8cc3a3149c8884ed4a18ccc2716f6d471b2cd8`.

Both new original receipts were independently reproduced byte for byte under
optimized Python: each 37 calls, 186 distinct instruction starts, seven producer
cases, ten mixed cases and complete checkpoint continuation. Producer execution
uses 41 starts, reads only actual manager ID, staff count and registry base/count,
and executes no call/system instruction. Slot execution retains the two original
classifiers. All twelve defect controls discriminate; all three unsupported
original probes remain censored, including the visible partial option-3 write.
No unsupported input is relabeled original rejection parity. The earlier failed
overstrict selector instrumentation attempt remains retained in research evidence.

The [retained receipt](evidence/human-registry-producer-oracle-v1.json) SHA-256 is
`15a41f8c213b01cc1774fc49e018af60ad251529058c2759d921bdcdb9069bfb`;
the [fresh receipt](evidence/fresh-human-registry-producer-oracle-v1.json) is
`8410886bcdc5c9b9e9c808cb28da8d2b27e157278de7cd214f78b5da28a551d4`.
Their pending-admission fields retain the generation-time authority; this separate
review approves only the exact fingerprints above. Private projection/audit files
remain outside Git, as do real exported states and raw captured bytes.
