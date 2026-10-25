# PC-R2 recovery

25 October 2026. This increment restores the pinned WSL development environment, fixes the two bounded process defects, and reproduces the accepted Bosman endpoint. Execution and comparison remain separate. The sanitized [receipt](evidence/pc-r2-recovery-2026-10-25.json) binds identities and outcomes; private paths and proprietary bytes remain outside Git.

## Environment and controls

The active WSL-native checkout is separate from the integration checkout and historical control. Rust 1.99.1 is installed with rustfmt, clippy and `wasm32-unknown-unknown`; no toolchain pin changed. WSL Node 18.19.1 supports the raw WebAssembly execution route used by PC-R1; browser/package engine qualification is separate. The coordinator retains ownership of workspace/lockfile/CI changes. Only one build or simulation owns the heavy slot at a time.

Nested smoke-runner stdout and stderr are drained incrementally with independent 1 MiB retained limits and a deadline; crossing either cap or silence beyond the deadline terminates the direct runner and returns failure. The enclosing supervisor contains and cleans up the full descendant tree. Admitted supervisor failures now publish canonical request, bounded captured streams and a failed replay manifest when the filesystem permits publication. Pre-admission validation/hash failures create no attempt. Per-file atomic writes publish the manifest last; storage or publication failure can leave an incomplete attempt and does not establish retained evidence.

## Scoped reconciliation

| Specimen or evidence | Identity and address scope | Admitted claim |
|---|---|---|
| Official 3.9.68 PE32 | SHA-256 `0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86`, 7,192,576 bytes; freshly hashed, parsed preferred image base `0x00400000` | This is the official instruction-emulation specimen; hashing does not exercise a process |
| CRT instruction oracle | Official VA `0x00946a04`, RVA `0x00546a04` | PC-R0/PC-R1 scoped wrapping CRT behaviour and explicitly exposed state |
| Small-bound oracle | Official VA `0x0090cfc0`, RVA `0x0050cfc0` | PC-R0/PC-R1 supported signed small-bound branch with synthetic table; large-bound x87/time initialization excluded |
| Bosman platform | Upstream `144ed82c248228c7769c6785899527eae5b33c3d`; retained executable SHA-256 `9a41f4a028f0dd1df71e3f9f18f9821a17f91947bb20e7ed0ba9fc18fcafa07b` | Independently versioned execution platform; fresh bounded clean classic same-save endpoint only |
| Reversal live GDI evidence | SHA-256 `0e50572c292bdfb9de8b3e087dd29043a13bcd0985ed198c9011e5a0f694388b`, updated data, private capture not recovered here | Method/reference metadata only; no transfer of addresses or behavioural qualification to the official specimen |
| Imported inventories | Reversal 9,241 inferred functions; map 11,747 starts | Independent inventory denominators, never an additive coverage total |

The [Reversal integration record](REVERSAL.md) retains instruction-oracle hashes and known exclusions. No live Windows helper, original startup, clean-data-consumption proof, original A/A or original/Bosman comparison was attempted. These remain separate gates under the [medium-helper contract](../architecture/PC_MEDIUM_HELPER_QUALIFICATION_V1.md).

## Reproduction and validation

The existing qualified Bosman binary, pinned smoke runner, clean-file manifest and Python interpreter were rehashed before a fresh immutable attempt. The adapter verifies all declared file identities and every clean-tree entry before and after execution. The fixed profile remains classic mode, two `normal,again` runs, seed 1, fixed clock, exactly 14 game days, positive normal idle-sleep count, byte-identical saves and final `PASS`.

Fresh attempt `pc-r2-same-save-20261025T092301Z` succeeded in 116.900 seconds including input verification; both nested runs reached 14 days in 85 seconds, with normal/again idle-sleep counts 20,964/20,995 and byte-identical saves. The runtime source was `8bd8ffb638c19b66acccfe986e1acfdb2eadcb32`. All 51 lab tests passed, including timeout/output/failure-publication controls; formatting and all-target clippy passed. The exact commands, tool versions and fresh artifact hashes are recorded in the receipt. A successful replay retains `comparison_verdict: not-run`; the endpoint's internal same-save assertion is not an observation-comparator result or an original-process fidelity claim. No Bosman rebuild, original launch, private capture recovery, unattended worker or infrastructure expansion was required.
