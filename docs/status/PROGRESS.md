# Programme progress

Updated: 24 October 2026 (Europe/London)

## Current checkpoint

- Roadmap revision 3 was validated, independently reviewed, and merged in PR #1 at commit `d750f3b9f8839994b4258ee5720c4b489fded9f7`.
- P00/B0 map-only inventory is active. No phase is complete.
- The two foundational public repositories are checked out outside the public repository at their selected commits. The source lock and deterministic map importer are implemented in the B0 delivery increment.

## Established facts

- Repository planning base was `b702984020767bd36095dc231354a77a97a9c2ff`.
- Host: Ubuntu 24.04.4 LTS, Linux 6.8, x86-64, 2 vCPU, 3.7 GiB RAM, no swap, and approximately 11 GiB free disk at inventory time.
- Rust `1.99.1` (`58cf8f9c35b355199727627d07ae34a4e2846d67`) and the `wasm32-unknown-unknown` standard library were installed for the B0 implementation.
- Git, Python 3.12, Node 22, npm 10.9, GCC 13, Make, Docker, Tailscale, SSH, and `xvfb-run` are present. CMake, PostgreSQL, Wine, Java, and .NET were not present at inventory time.
- No CM01/02 executable, ISO, original database/assets, reference save, or earlier CM0102 upstream checkout was found in bounded searches of `/root`, `/mnt`, `/opt`, `/srv`, and `/var/lib`.

## Evidence and blockers

- The reviewed roadmap bundle SHA-256 was `0c930b0c4db9dffb77ec02994225ad2ee9d457d3b679007b395cfea8ee5c3645`; all 31 overlay hashes and document checks passed before merge.
- The selected Bosman and function-map commits resolve remotely and locally. Their exact identities are recorded in `config/upstream-lock.json`.
- The real pinned map import produced 11,747 broad function starts, 6,863 function records, 6,863 name records, 1,161 not-high records, 4,428 global records, and 4,428 data records. All six tables had zero duplicate addresses; the broad inventory contained 4,884 addresses not present in the named-function table, while every named function was present in the broad inventory.
- Two independent executions of the reviewed importer produced byte-identical 19,892,857-byte JSON artifacts with SHA-256 `5b4b8d61103bf63537f5ae32810081be9327b75aebac77c26ad901776d0798fb`. Generated evidence remains untracked.
- Original executable/data identity, PE section validation, original process observations, Bosman build qualification, and original/Bosman parity are blocked by absent authorized original inputs.
- The current host is below the roadmap's provisional 4 vCPU / 8 GiB / 80 GiB-free pilot envelope. This is a measurement constraint, not a purchase request; no 24-hour worker pilot is scheduled.
- Off-host backup destination remains unset, so unattended durability cannot be certified.

## Next bounded actions

1. Maintain the deterministic B0 map import, provenance report, reconciliation, and negative tests as the upstream inventory evolves through reviewed pin changes.
2. Expand the coverage register from direct observation when qualified original inputs become available.
3. Obtain or locate the authorized official 3.9.68 executable, matching original 2001 data/assets, and reference saves in a private input area; hash and qualify them without committing bytes.
4. Only then install the remaining B1 build dependencies needed by the pinned Bosman instructions, build it separately, and run one isolated Rust-CLI job with a replay manifest.

## Model routing record

- Lead/integration: current Codex coordinator model.
- Roadmap reconciliation and independent planning review: `gpt-6-astra`, extra-high reasoning (available substitute for the requested 6.1 Sol reviewer).
- Host/upstream inventory and bounded importer implementation: `gpt-5.6-luna`, high reasoning (available substitute for the requested 6 Luna worker).
