# P00 private-input qualification

Date: 24 October 2026 (Europe/London)

## Transfer evidence

The user authorized read-only access to an installed Windows copy. The source installation was not modified. It was copied to a private, repository-external input area and both sides were hashed file by file before qualification.

- Files: 774
- Bytes: 855,766,040
- Source manifest SHA-256: `17d6b31dfb0835604b6ad27e8a16d4c7d316be5bf209871c9b2f523b8a439e63`
- Destination manifest SHA-256: `17d6b31dfb0835604b6ad27e8a16d4c7d316be5bf209871c9b2f523b8a439e63`
- File-level comparison: no differences
- Distribution: private only; no original bytes or private paths are committed

## Executable result

The executable is qualified as the exact official 3.9.68 image required by Bosman commit `144ed82c248228c7769c6785899527eae5b33c3d`.

| Property | Value |
|---|---|
| SHA-256 | `0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86` |
| File size | 7,192,576 bytes |
| Format | PE32/i386 Windows GUI |
| Image base | `0x00400000` |
| Image size | 10,383,360 bytes |
| Entry point VA | `0x00947a13` |
| Sections | `.text`, `.rdata`, `.data`, `.rsrc` |

The Rust importer rejects any other executable hash before parsing its PE headers. With this image, every pinned function/name address falls in a code section and every global/data address falls in a mapped section. Two complete imports were byte-identical at 19,894,555 bytes with SHA-256 `5e411cf01746c8b0defd8503a0b61efbfc36c3547649162c95df56a18d636510`.

## Installed-folder result

The installed folder is not a clean baseline. The comparison used the clean manifest at pinned Bosman commit `144ed82c248228c7769c6785899527eae5b33c3d`, manifest SHA-256 `920cbf75653473d276cd33fbbe7a90553dcd6fff4c0878e848aaca7736dddac6`, with Windows-case-insensitive path matching.

| Classification | Files |
|---|---:|
| Required by clean manifest | 760 |
| Exact | 696 |
| Changed | 57 |
| Missing | 7 |
| Extra | 21 |

The changed required files are concentrated in `Data` plus `hall_of_fame.bin`; missing and corresponding extra history entries include filename-encoding differences. Extras also include configuration, quick-start, tactic, utility, uninstall, and save files. These facts do not identify the changed database as original 2001 data, so it cannot be relabelled as the faithful baseline.

## Separate clean reconstruction

The user's official free-release ISO and official 3.9.68 patch were subsequently located outside the installed folder. Their sizes and SHA-256 values exactly match the constants enforced by the pinned clean-file tool: `853134bbfc9e774424e62f9694ad7fe9dd7361c8bab93033f82fc906b31a5c53` for the 303,628,288-byte ISO and `b3f2b7d2ace6e86d0974e5ad68ae7a87a1e8fc3494c90d00cc3758392dcf24f1` for the 23,458,816-byte patch.

The pinned tool reconstructed a new private, read-only folder without changing the installed game. All 760 files and 483,574,706 bytes match the committed clean manifest; the generated and committed manifests are byte-identical at SHA-256 `920cbf75653473d276cd33fbbe7a90553dcd6fff4c0878e848aaca7736dddac6`. The clean baseline input is therefore qualified. The original installed folder remains classified as modified and is retained only as a separate diagnostic input.

## Build and runtime evidence

The pinned Bosman build dependencies were installed from the upstream Linux recipe. A VPS build passed configuration and generated-table checks, but the kernel OOM killer terminated the static recompiler at approximately 3.06 GiB resident memory. The temporary build-only swap file was removed when work moved to the larger PC/WSL worker.

The PC/WSL worker has 16 logical CPUs, 7.7 GiB RAM, 2 GiB configured swap, and 937 GiB free WSL disk. After the peer was restored, the pinned Release build completed in 11 minutes 19.72 seconds with a peak resident set size of 7,547,840 KiB. Temporary build-only swap prevented an OOM kill and was removed afterward. The resulting 48,696,400-byte x86-64 ELF has SHA-256 `9a41f4a028f0dd1df71e3f9f18f9821a17f91947bb20e7ed0ba9fc18fcafa07b`; all 45 registered upstream tests pass with the documented `draw_test` link workaround. Full evidence is in [B1 Bosman build evidence](B1_BOSMAN_BUILD.md).

Two upstream classic-mode smoke runs against the reconstructed clean set passed through first news and holiday date advancement. The second run reproduced setup, league selection, and first news exactly under the pinned runner's smoke policy. That ordinary runner did not fix seed/clock state, so these are not deterministic replay evidence. Full measurements and evidence identities are in [B1 clean-data smoke evidence](B1_CLEAN_SMOKE.md). Clean data is no longer a blocker; the remaining B1 boundary is the repository's Bosman-specific protocol adapter and replay manifest.
