# Synthetic RNG corpus

`corpus.bin` is a lossless little-endian integer projection of the public synthetic
oracle at Reversal revision `9b0d1a5fa5dd6c9dc8f4efc69e14bcd49c052345`.
SHA-256: `2b73d884b5e360d5443b4691573416838eb3550d27b6277521e52a6490098c9e`.
The first three u32 words are CRT/bounded/sequential counts. Each CRT record is
initial CRT, expected value, expected final CRT. Each bounded record is signed
bound, initial cursor/offset/CRT, expected signed value, final cursor/offset/CRT.
Signed fields use two's complement. All records remain in oracle order.

The synthetic table is generated in the runner from seed `0x10203968` using the
specified CRT recurrence. No original executable or actual-game table bytes are
included. `scripts/r1/prepare_corpus.py` regenerates the projection only after
checking the exact upstream oracle and synthetic-table SHA-256 identities.

Reversal source and synthetic oracle: Copyright (c) 2026 Derek Rivers, MIT;
see `UPSTREAM_LICENSE`. Port and projection attribution: Derek Rivers, 2026.
The upstream MIT permission does not grant rights to redistribute original game
material. See `docs/research/PC_R1_RNG.md` for scope and validation commands.
