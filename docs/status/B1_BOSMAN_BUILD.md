# B1 Bosman build evidence

Date: 24 October 2026 (Europe/London)

## Scope and identity

This checkpoint qualifies a native Linux build of the pinned Bosman source. It does not qualify runtime behaviour or close B1: the available installed data is not the clean 760-file baseline. A later exploratory run against those modified files reached first news, but is deliberately excluded from this build qualification and from baseline evidence.

| Property | Value |
|---|---|
| Bosman commit | `144ed82c248228c7769c6785899527eae5b33c3d` |
| Source-tree changes | none |
| Input executable SHA-256 | `0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86` |
| CMake build type | `Release` |
| Output format | ELF 64-bit LSB PIE, x86-64, dynamically linked |
| Output size | 48,696,400 bytes |
| Output SHA-256 | `9a41f4a028f0dd1df71e3f9f18f9821a17f91947bb20e7ed0ba9fc18fcafa07b` |

The private executable path, generated C, and built binary remain outside this repository. No original or generated game bytes are committed.

## Worker and toolchain

- Kernel: Linux `6.6.87.2-microsoft-standard-WSL2`, x86-64.
- Worker allocation during the build: 16 logical CPUs, 7.7 GiB RAM, 2 GiB configured WSL swap.
- Toolchain: CMake 3.28.3, Ninja 1.11.1, GCC 13.3.0, Python 3.12.3, Capstone 5.0.6, and SDL2 2.30.0.
- Build command shape: `cmake --build <private-build-dir> -j 8 --target cm0102_recomp`.

The static-recompilation phase exceeded physical WSL memory. Two temporary 8 GiB build-only swap files prevented an OOM kill. Both were disabled and deleted after the build; only WSL's configured 2 GiB swap remains. Peak resident set size was 7,547,840 KiB. The successful build took 11 minutes 19.72 seconds and exited with status 0.

## Translation report

The generated report is 3,031 bytes with SHA-256 `e3bdaea3e62855ede6e73485efdcc072a25c77582ddec0f07cb892b2704ff827`. The private build contains 129 generated C files totalling 181,952,305 bytes.

| Metric | Result |
|---|---:|
| Functions | 11,748 |
| Decoded instructions | 1,882,031 |
| Handled instructions | 1,882,000 |
| Handled share | 99.9983528433% |
| Unhandled instructions | 31 |
| Decode stops | 1 |
| Jump tables | 1,266 |
| Resume entries | 11 |
| Missing-function targets | 3 |

The report explicitly lists every unhandled instruction and missing target. These counts are translation evidence, not a claim of behavioural fidelity or whole-game completion.

## Upstream tests

All 45 registered CTest cases passed in 11.50 seconds.

Two pinned upstream Linux build-system defects were separated from product behaviour:

1. The default `all` target compiles `src/si/exe_image.c`, which unconditionally includes Apple's `CommonCrypto/CommonDigest.h`; this target therefore fails on Linux. The qualified `cm0102_recomp` target does not use that file and built successfully.
2. `draw_test` calls `lround()` but its CMake target does not link `libm`. Its existing two object files were linked manually with the otherwise identical link command plus `-lm`; the source checkout was not modified. With that build-only correction, all 45 tests passed.

The other 44 tests used their pinned CMake definitions without changes. A future upstream integration patch should add `m` to `draw_test` and make the `CommonCrypto` implementation platform-specific, then rerun this evidence without manual workarounds.

## Gate status

The pinned source, exact executable input, generated translation, native binary identity, resource envelope, and applicable upstream unit tests are now qualified. B1 remains open until clean data is reconstructed and validated, the Bosman-specific process adapter runs one isolated job, the expected endpoint is observed, and logs plus a replay manifest are retained. No runtime or original/Bosman parity claim is made here.
