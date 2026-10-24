# B0 map import evidence

Date: 24 October 2026 (Europe/London)

## Source identity

- Function map repository: `https://github.com/maxevans60/cm0102-function-map`
- Commit: `2bb558ef6a6bcdbd304dd1a6a4cf156c6707007c`
- Git tree: `ab79904e2c3fb0217be9df7c6a53f6bebd655dd5`
- Import format: `b0-map-import-v1`
- Lock: `config/upstream-lock.json`
- Address validation: `pending_executable`
- Semantic status of every imported record: `imported-hypothesis`

The checkout commit, each TSV hash, row count, required header, and address syntax were verified before import. Extra columns are retained by name. No RVA was derived because the original executable and PE section map are not available.

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

Two clean CLI executions produced byte-identical artifacts:

- Size: 19,892,857 bytes
- SHA-256: `5b4b8d61103bf63537f5ae32810081be9327b75aebac77c26ad901776d0798fb`

The full generated artifact is under ignored `target/b0-evidence/` and is not committed. It can be regenerated with the command in the repository README. Tests cover strict lock lookup, required-header rejection, malformed and out-of-range addresses, canonical numeric duplicate detection, physical row identity, unknown-column preservation, duplicate surfacing, hash and row-count drift, distinct denominators, and deterministic serialization.

Verification commands:

```sh
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo run --quiet -p lab-cli -- import-map \
  --source-dir /path/to/the/pinned/function-map \
  --lock-manifest config/upstream-lock.json \
  --output target/b0-evidence/function-map-import.json
```

## Gate status

B0 map ingestion and public-source pinning are implemented. P00 remains open: original executable/data/assets/save identity, PE validation, direct feature enumeration, and qualified reference execution are missing. B1 cannot run until authorized original inputs are available.
