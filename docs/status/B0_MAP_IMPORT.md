# B0 map import evidence

Date: 24 October 2026 (Europe/London)

## Source identity

- Function map repository: `https://github.com/maxevans60/cm0102-function-map`
- Commit: `2bb558ef6a6bcdbd304dd1a6a4cf156c6707007c`
- Git tree: `ab79904e2c3fb0217be9df7c6a53f6bebd655dd5`
- Import format: `b0-map-import-v1`
- Lock: `config/upstream-lock.json`
- Executable SHA-256: `0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86`
- Address validation: `validated_va_against_official_3.9.68_pe32`
- Semantic status of every imported record: `imported-hypothesis`

The checkout commit, executable hash, each TSV hash, row count, required header, and address syntax were verified before import. Extra columns are retained by name. The executable is PE32/i386 with image base `0x00400000`, image size `10,383,360` bytes, and entry point VA `0x00947a13`. All 11,747 broad starts, 6,863 function records, 6,863 names, and 1,161 not-high rows resolve to a code section. All 4,428 globals and 4,428 data descriptions resolve to mapped PE sections. Validation establishes address placement, not semantics.

## Reconciled results

| Table | Rows | Unique addresses | Duplicate addresses |
|---|---:|---:|---:|
| Broad function starts | 11,747 | 11,747 | 0 |
| Function records | 6,863 | 6,863 | 0 |
| Name records | 6,863 | 6,863 | 0 |
| Not-high records | 1,161 | 1,161 | 0 |
| Globals | 4,428 | 4,428 | 0 |
| Data descriptions | 4,428 | 4,428 | 0 |

Cross-table reconciliation:

- Broad addresses absent from function records: 4,884. These remain in the inventory denominator and include runtime/unwind/unnamed categories; they are not deleted as “unmapped noise.”
- Function addresses absent from the broad inventory: 0.
- Function/name mismatches: 0 in either direction.
- Not-high addresses absent from the broad inventory: 0.
- Globals/data mismatches: 0 in either direction.

These counts reconcile the upstream README's reported catalogue sizes against the actual pinned TSV bytes. They establish inventory, not behaviour or completeness of the whole game.

## Repeatability and checks

Two clean CLI executions with the exact executable produced byte-identical artifacts:

- Size: 19,894,555 bytes
- SHA-256: `5e411cf01746c8b0defd8503a0b61efbfc36c3547649162c95df56a18d636510`

The full generated artifact is under ignored `target/b0-evidence/` and is not committed. It can be regenerated with the command in the repository README. Tests cover strict lock lookup, required-header rejection, malformed and out-of-range addresses, canonical numeric duplicate detection, physical row identity, unknown-column preservation, duplicate surfacing, hash and row-count drift, distinct denominators, and deterministic serialization.

Verification commands:

```sh
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo run --quiet -p lab-cli -- import-map \
  --source-dir /path/to/the/pinned/function-map \
  --lock-manifest config/upstream-lock.json \
  --executable /private/path/to/cm0102.exe \
  --output target/b0-evidence/function-map-import.json
```

## Gate status

B0 map ingestion, public-source pinning, exact executable identity, PE validation, and map-address placement are implemented. P00 remains open: the supplied installed data differs from the pinned clean manifest, assets and candidate saves are not fully qualified, direct feature enumeration is incomplete, and no reference execution is qualified. B1 runtime execution needs the official ISO plus 3.9.68 patch, or another independently verified way to reconstruct the matching clean data.
