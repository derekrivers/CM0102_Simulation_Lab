# PC-R1: qualified portable RNG slice

Scope: `cm-rng`, original-instruction corpus, synthetic table, explicit state,
native and executed WASM equality. This is not a whole-game or original-process
parity claim. x87 large bounds, OS-time seeding, initialization, actual-game table,
original-save compatibility and additional RNG sources remain excluded.

## Original contract and frozen domain

Before implementation, the worker hash-verified the private official executable as
`0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86`
and inspected it with GNU objdump (`-D -Mintel`, ranges VA 0090cfc0..0090d040
and 00946a04..00946a22). No executable bytes are retained here.

At 0090cfca the zero case returns before cursor mutation. At 0090cfda the cursor
advances by four bytes; unsigned JBE at 0090cfe5 includes the final word. Beyond
that word, 0090cfe7 resets to table start and calls CRT once; 0090cffc masks its
return with FFFF. At 0090d00d/0090d015 signed comparisons select bounds
-65535 through 65535. ADD, CDQ, IDIV at 0090d01d..0090d020 specify a wrapping
32-bit signed dividend and signed remainder; negative bounds negate remainder.
CRT at 00946a09 uses low-32-bit IMUL by 343FD and ADD 269EC3, stores the state,
then SAR16 and AND7FFF. Unsigned shift plus mask in Rust has the same result.
TypeScript was a secondary comparison source, not the only authority.

Frozen admitted domain:

- Table has exactly 51,000 immutable u32 words, each 0..32767 inclusive.
- Cursor is a signed word index -1..50999 inclusive; -1 denotes before first word.
- Offset is 0..65535 inclusive; CRT state admits every u32 bit pattern.
- Bound is i32 in -65535..65535 inclusive. Zero consumes no state.

The table-word restriction deliberately follows the qualified synthetic fixture.
The admitted offset plus word cannot overflow signed i32, so x86 division traps
are excluded. Wider table values and offsets are rejected rather than silently
claimed as supported. Explicit wrapping is retained for CRT and dividend ADD.
State/table construction validates before exposure; unsupported bounds validate
before mutation. Table identity is SHA-256 over all little-endian u32 words.
A sampled corpus supports these observations; it is not exhaustive domain proof.

## Interface and checkpoint

Production `cm-rng` is `#![no_std]` with no allocation or host services. Its only
dependency is `sha2` without default features. `crt_step(&mut u32)` returns a
15-bit draw. `Table::new(&[u32])` validates borrowed immutable words and hashes
them. `Rng::new(Table, State)` validates explicit state. `next_bounded(i32)`
returns a result or an error; rejection preserves the RNG. `state()` exposes
all mutable fields.

Checkpoint v1 is exactly 52 bytes: ASCII CMRG (4), LE u32 version=1 (4), SHA-256
table identity (32), LE i32 cursor (4), LE u32 offset (4), LE u32 CRT (4).
`restore` requires exact length/magic/version/table identity and valid state.
The table is injected again; the checkpoint does not embed it. Rejected restore
constructs no RNG and changes no existing RNG. This is a new portable format,
not an original saved-game format.

## Provenance and reproduction

Reversal pin: `9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345`, MIT, Copyright
(c) 2026 Derek Rivers. The upstream licence and attribution accompany the public
synthetic projection. Sources: `scripts/emulate_random.py`,
`reconstruction/bounded-random.ts`, `reconstruction/check-random.ts`, and
`evidence/random-validation`. The existing [R0 receipt](evidence/reversal-rng-2026-10-25.json)
records fresh original-instruction regeneration and exact retained-byte equality.

Oracle SHA-256: `b7794145182f3ee357c11bf53136351c4231b960ae8c69d560ab2732a2d2f692`.
Synthetic table SHA-256: `befdec88f802582bba7450e418aaa39837036c8d038810158cfc7a998be1b3db`.
Compact corpus SHA-256: `2b73d884b5e360d5443b4691573416838eb3550d27b6277521e52a6490098c9e`.
No goldens were changed. Native/WASM runner generates the same synthetic table.

From the WSL checkout, with root workspace membership and pinned toolchain:

```sh
source ~/.cargo/env
python3 scripts/r1/prepare_corpus.py /path/to/pinned/reversal/evidence/random-validation
python3 scripts/r1/verify.py /tmp/cm-r1-fresh-output
```

The output directory must be new. Verification checks formatting, unit rejection
cases, Clippy warnings, native and wasm builds, and executes the same Rust corpus
through native code and Node's actual WebAssembly engine. Compilation alone is
not accepted. Native output uses stdout; WASM exports pointer/length into memory.
Each path asserts 1,024 CRT returns/states and 2,570 bounded returns/states.
The final 512 calls additionally compare chained initial state and checkpoint
restore/continuation (511 subsequent calls), including wrap and zero calls.

Canonical output is LE CRT value/state pairs, bounded value/cursor/offset/CRT
records, a 52-byte checkpoint after each sequential call, then four u32 negative
control mismatch counts. First execution produced 75,952 bytes in each runtime,
SHA-256 `1c8d5c5b3443386e18f2124f19dcebbde7999124e3b557b71f78507597ce0d16`.
Both bytes and pinned canonical hash must match.

Independent faulty transition controls discriminate multiplier343FC (1,023
CRT-state mismatches), wrap one word early (61 state mismatches), extra CRT draw
on every nonzero call (2,447 state mismatches), and cursor increment on zero
(123 state mismatches). Controls are explicit separate faulty models in the
runner; production has no mutation switches. Tests also reject unsupported bound,
state, table length/word, malformed checkpoint, and wrong table identity.

The implementation worker ran the supplied model selected by the coordinator;
no unavailable model selection is claimed. Independent review of the final
revision and integration checks remain coordinator responsibilities.

Final fresh verification receipt: [PC-R1 execution](evidence/pc-r1-rng-2026-10-25.json).
The default `cargo test -p cm-rng` also executes the complete shared corpus via
`tests/original_corpus.rs`; the native/WASM example uses the same Rust harness.
The runner explicitly checks the generated synthetic table's pinned SHA-256.
GNU objdump used for contract inspection was Ubuntu Binutils 2.42.
