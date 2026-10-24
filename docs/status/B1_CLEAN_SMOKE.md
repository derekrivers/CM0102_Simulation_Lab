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

The pinned native build `9a41f4a028f0dd1df71e3f9f18f9821a17f91947bb20e7ed0ba9fc18fcafa07b` ran the upstream classic-mode smoke scenario against the reconstructed clean set with an isolated temporary user directory. The runner was `tests/smoke/smoke_run.py` at the pinned Bosman commit, SHA-256 `3428aeae65a2dcd899e123b8c9649d109404cd11c601d2c89947d872d8d7196b`, under Python 3.12.3. The command shapes were:

```sh
python3 tests/smoke/smoke_run.py "$PINNED_BOSMAN_BIN" "$CLEAN_GAME_DIR" "$PRIVATE_EVIDENCE_DIR" --mode classic --record
python3 tests/smoke/smoke_run.py "$PINNED_BOSMAN_BIN" "$CLEAN_GAME_DIR" "$PRIVATE_EVIDENCE_DIR" --mode classic
```

No `--database` or `--tolerance` argument was supplied, so the run used the default 3.9.68 data directory and zero per-channel colour tolerance. The ordinary smoke path creates a private temporary `HOME`, `RECOMP_USER_DIR`, and classic `settings.txt`; sets dummy SDL audio/video plus the scripted UI route; and has a 300-second process timeout. Unlike the runner's separate `--same-save` mode, this ordinary path does not pass `-seed 1` or set `RECOMP_FIXED_CLOCK=1`. Its RNG/clock state is therefore not claimed as controlled, and these runs are startup-path smoke evidence rather than deterministic replay evidence.

Run 1 recorded settings, setup, league selection, first news on 14 July 2001, and a holiday date-advance check. It passed in 1 minute 18.47 seconds with peak RSS 183,204 KiB and no swap. Run 2 compared against that record:

| Check | Repeat result |
|---|---:|
| first-settings random background | 14.1% pixels differ; allowed 20% |
| setup | 0.0%; exact |
| league selection | 0.0%; exact |
| first news | 0.0%; exact |
| holiday date box | 100% changed from first news, as required |

The comparison policy comes directly from that pinned runner: the randomized first-settings background permits at most 20% differing pixels; setup, league selection, and first news permit 0%; and the holiday date box must change by more than 2%. These are upstream smoke assertions, not newly chosen fidelity tolerances. Run 1's `--record` path saved images without comparing them; run 2 applied the policy above.

Run 2 passed in 1 minute 15.32 seconds with peak RSS 183,492 KiB, no swap, and exit status 0. The private six-file evidence set is 6.9 MiB:

| Relative artifact | SHA-256 |
|---|---|
| `classic/1-settings.bmp` | `e7005c5fb3a6b6a1a521a6ac0689aed38c8cad7d1d6af643ce9606c6bae3f10b` |
| `classic/2-setup.bmp` | `797daf6c9b627eef00ff24cc759d34624e1ff12d340f86dcd56ee7be0f6efa16` |
| `classic/3-leagues.bmp` | `cdaed061f71f24a6c1c2e01d56ba02b955b535165be75141f0ecefd81427775d` |
| `classic/4-news.bmp` | `ac0991155dc969af68c4c999bb5aa5f1e155918284edc8a7f5a1ae9bc943aca0` |
| `classic/5-holiday.bmp` | `5bd89cc80a28a5480573dc03ac1d0eee740823bbd4e583034447aa87553b8808` |
| `replay-a2.log` | `c5249a5940db26cf3e58ab3e941206ba94b90e44267e9105267e18431c8c2094` |

The digest-list aggregate `3507a688ea96adc5d89503c38f9927bb92b40ad5797cc60e27d84e866934c4ac` is the SHA-256 of the lexically path-sorted `sha256sum` output for those six files, using `./`-prefixed relative paths. Only run 2 has a retained console/resource log; run 1 retains its five screenshots and the measurements recorded during the supervised invocation.

## Scope

This qualifies clean input identity and records two successful upstream startup/first-news/holiday smoke observations under the stated policy. It removes the clean-data blocker, but does not claim deterministic replay because the ordinary runner did not fix seed/clock state. It does not by itself close B1: the Bosman-specific protocol adapter must still produce the repository's versioned request, controlled execution context, captured logs, endpoint record, and replay manifest. It is not an original-versus-Bosman fidelity comparison.
