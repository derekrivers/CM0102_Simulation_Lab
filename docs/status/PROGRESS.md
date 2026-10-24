# Programme progress

Updated: 24 October 2026 (Europe/London)

## Current checkpoint

- Roadmap revision 3 was validated, independently reviewed, and merged in PR #1 at commit `d750f3b9f8839994b4258ee5720c4b489fded9f7`.
- The pinned B0 map inventory importer was independently reviewed, corrected, re-reviewed with no findings, and merged in PR #2 at commit `28928e649d75b01dabe61b5cdcb9cc81cbbde3a7`.
- The executable/input qualification and PE-backed map-address validation were independently reviewed with no findings and merged in PR #4 at commit `0e64c4acfea612de58409639f5bed7241c7d94a7`.
- A user-authorized Windows installation was copied to private storage and verified file-for-file against source hashes. Its `cm0102.exe` exactly matches official 3.9.68 as required by the pinned Bosman source.
- The pinned Bosman source now has a qualified native Linux Release build on the PC/WSL worker. All 45 registered upstream tests pass. A bounded local execution-request validator and protocol process supervisor are implemented with synthetic contract tests; the Bosman-specific protocol adapter remains outstanding.
- P00/B0 input inventory is active. No phase is complete.
- The two foundational public repositories are checked out outside the public repository at their selected commits. The source lock and deterministic map importer are implemented in the B0 delivery increment.

## Established facts

- Repository planning base was `b702984020767bd36095dc231354a77a97a9c2ff`.
- Host: Ubuntu 24.04.4 LTS, Linux 6.8, x86-64, 2 vCPU, 3.7 GiB RAM, no swap, and approximately 11 GiB free disk at inventory time.
- Rust `1.99.1` (`58cf8f9c35b355199727627d07ae34a4e2846d67`) and the `wasm32-unknown-unknown` standard library were installed for the B0 implementation.
- Git, Python 3.12, Node 22, npm 10.9, GCC 13, Make, Docker, Tailscale, SSH, and `xvfb-run` are present. CMake, PostgreSQL, Wine, Java, and .NET were not present at inventory time.
- No CM01/02 executable, ISO, original database/assets, reference save, or earlier CM0102 upstream checkout was found in bounded searches of `/root`, `/mnt`, `/opt`, `/srv`, and `/var/lib`.
- A Windows/WSL worker is now available over Tailscale with 16 logical CPUs, approximately 11 GiB usable RAM, 12 GiB configured swap, and ample WSL disk. It is the preferred heavy build/experiment host while the VPS remains the coordinator. Its WSL/Tailscale availability must be kept persistent for unattended work.

## Evidence and blockers

- The reviewed roadmap bundle SHA-256 was `0c930b0c4db9dffb77ec02994225ad2ee9d457d3b679007b395cfea8ee5c3645`; all 31 overlay hashes and document checks passed before merge.
- The selected Bosman and function-map commits resolve remotely and locally. Their exact identities are recorded in `config/upstream-lock.json`.
- The real pinned map import produced 11,747 broad function starts, 6,863 function records, 6,863 name records, 1,161 not-high records, 4,428 global records, and 4,428 data records. All six tables had zero duplicate addresses; the broad inventory contained 4,884 addresses not present in the named-function table, while every named function was present in the broad inventory.
- Two independent executions of the reviewed importer produced byte-identical 19,892,857-byte JSON artifacts with SHA-256 `5b4b8d61103bf63537f5ae32810081be9327b75aebac77c26ad901776d0798fb`. Generated evidence remains untracked.
- The transferred private installation contains 774 files and 855,766,040 bytes. Source and destination file manifests are identical, each with SHA-256 `17d6b31dfb0835604b6ad27e8a16d4c7d316be5bf209871c9b2f523b8a439e63`.
- The executable has SHA-256 `0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86`, size 7,192,576 bytes, PE32/i386 image base `0x00400000`, and entry point VA `0x00947a13`. This exactly matches the pinned Bosman hash.
- Against Bosman's 760-file clean manifest, the installed folder has 696 exact files, 57 changed files, 7 missing files, and 21 extras under Windows-case-insensitive path comparison. It is not the clean data baseline. The official ISO and patch installer were not found in bounded Windows user-folder searches.
- Two executable-backed map imports validated every address against the PE sections and produced byte-identical 19,894,555-byte artifacts with SHA-256 `5e411cf01746c8b0defd8503a0b61efbfc36c3547649162c95df56a18d636510`.
- The first VPS Bosman build reached static recompilation but the kernel killed its 3.06 GiB Python process on the 3.7 GiB/no-swap host. The PC/WSL Release build subsequently completed in 11 minutes 19.72 seconds with peak RSS 7,547,840 KiB. Its 48,696,400-byte x86-64 ELF has SHA-256 `9a41f4a028f0dd1df71e3f9f18f9821a17f91947bb20e7ed0ba9fc18fcafa07b`.
- The translation report records 1,882,000 handled instructions out of 1,882,031 (99.9983528433%), 31 explicitly listed unhandled instructions, one decode stop, and three missing-function targets. All 45 registered CTest cases pass. The source checkout remained clean; `draw_test` needed a build-only `-lm` link correction, and the unrelated default demo target has an upstream Linux `CommonCrypto` include defect.
- An explicitly non-baseline diagnostic run used isolated classic-layout settings and the modified installed data. The pinned Bosman build reached first news and exited zero in 2 minutes 3.43 seconds with peak RSS 177,080 KiB. This establishes that the build can traverse the startup UI on the available data; it is not qualified replay or fidelity evidence because the data differ from the clean manifest and the exploratory console log was not retained as a durable protocol artifact.
- The local process-contract increment rejects unknown request fields, hash mismatches before spawn, inherited environment secrets, malformed or misordered NDJSON, handshake identity mismatch, missing/wrong terminal endpoints, output overflow, timeout survivors, and attempt-directory reuse. Successful synthetic executions atomically publish hashed stdout, stderr, and a replay manifest whose comparison verdict is `not-run`. The direct Bosman binary is not yet connected to this protocol.
- Independent review initially found a canonical-lock bypass plus physical-row and equivalent-address defects. Strict direct lock paths, numeric address canonicalization, physical-row retention, and regression tests resolved all three before PR #2 merged.
- Matching original data identity, qualified Bosman runtime execution, original process observations, and original/Bosman parity remain blocked. The executable, PE section layout, Bosman native build, and upstream unit tests are qualified; the installed data is not clean.
- The current host is below the roadmap's provisional 4 vCPU / 8 GiB / 80 GiB-free pilot envelope. This is a measurement constraint, not a purchase request; no 24-hour worker pilot is scheduled.
- Off-host backup destination remains unset, so unattended durability cannot be certified.

## Next bounded actions

1. Maintain the deterministic B0 map import, provenance report, reconciliation, and negative tests as the upstream inventory evolves through reviewed pin changes.
2. Expand the coverage register from direct observation when matching data and a qualified execution path become available.
3. Locate the official `CM0102.iso` and `cm0102_3968.exe`, verify their pinned hashes privately, and reconstruct the clean 760-file runtime set without committing bytes.
4. Implement the Bosman-specific UI-driving protocol adapter and exercise it first as a clearly labelled non-baseline diagnostic against the available modified data.
5. After clean data qualification, run the same bounded Bosman job with endpoint evidence, logs, and a replay manifest; only then consider the B1 clean-baseline gate.

## Model routing record

- Lead/integration: current Codex coordinator model.
- Roadmap reconciliation and independent planning review: `gpt-6-astra`, extra-high reasoning (available substitute for the requested 6.1 Sol reviewer).
- Host/upstream inventory and bounded importer implementation: `gpt-5.6-luna`, high reasoning (available substitute for the requested 6 Luna worker).
