# B1 clean-data smoke evidence

Date: 24 October 2026 (Europe/London)

## Clean input reconstruction

The user's existing Windows installation was not modified. The pinned `make_clean_files.py` tool reconstructed a separate private runtime set from these user-provided official inputs:

| Input | Bytes | SHA-256 |
|---|---:|---|
| `CM0102.iso` | 303,628,288 | `853134bbfc9e774424e62f9694ad7fe9dd7361c8bab93033f82fc906b31a5c53` |
| official 3.9.68 patch | 23,458,816 | `b3f2b7d2ace6e86d0974e5ad68ae7a87a1e8fc3494c90d00cc3758392dcf24f1` |

Both identities are hard-coded by the clean-file tool at Bosman commit `144ed82c248228c7769c6785899527eae5b33c3d`. Extraction reported 752 cabinet files and 46 patch entries. The result contains exactly 760 files and 483,574,706 bytes; its generated manifest is byte-identical to the pinned manifest with SHA-256 `920cbf75653473d276cd33fbbe7a90553dcd6fff4c0878e848aaca7736dddac6`. The tool identified `cm0102.exe` as 3.9.68 and all 760 size/hash rows passed. The clean source set is private and read-only.

As a separate cross-check, the published Bosman v0.5.0 Linux AppImage had the SHA-256 listed in its release `SHA256SUMS`, `6ab3817eddcd4920246901ab71eb9d36b9e8db5221afb807e0a4348cce36c24d`. Its game directory contained the same 760 clean files plus 41 clearly separated release additions. Copying only the pinned manifest paths produced a second 760/760 match. This cross-check is not a substitute for the official-input reconstruction above.

## Clean smoke and repeat

The pinned native build `9a41f4a028f0dd1df71e3f9f18f9821a17f91947bb20e7ed0ba9fc18fcafa07b` ran the upstream classic-mode smoke scenario against the reconstructed clean set with an isolated temporary user directory.

Run 1 recorded settings, setup, league selection, first news on 14 July 2001, and a holiday date-advance check. It passed in 1 minute 18.47 seconds with peak RSS 183,204 KiB and no swap. Run 2 compared against that record:

| Check | Repeat result |
|---|---:|
| first-settings random background | 14.1% pixels differ; allowed 20% |
| setup | 0.0%; exact |
| league selection | 0.0%; exact |
| first news | 0.0%; exact |
| holiday date box | 100% changed from first news, as required |

Run 2 passed in 1 minute 15.32 seconds with peak RSS 183,492 KiB, no swap, and exit status 0. The private six-file evidence set is 6.9 MiB. Its digest-list aggregate is `3507a688ea96adc5d89503c38f9927bb92b40ad5797cc60e27d84e866934c4ac`; the durable repeat log SHA-256 is `c5249a5940db26cf3e58ab3e941206ba94b90e44267e9105267e18431c8c2094`.

## Scope

This qualifies clean input identity and a repeatable upstream startup/first-news/holiday smoke path. It removes the clean-data blocker. It does not by itself close B1: the Bosman-specific protocol adapter must still produce the repository's versioned request, captured logs, endpoint record, and replay manifest. It is not an original-versus-Bosman fidelity comparison.
