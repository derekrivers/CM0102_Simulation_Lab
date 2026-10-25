# Backend capability matrix

Status: reconciled 25 October 2026; scoped evidence only. `pending` means no qualified local execution supports the capability yet; it is not equivalent to false or unsupported in the upstream project.

| Capability | original-windows | original-function | bosman-native | rust-native | rust-wasm |
|---|---|---|---|---|---|
| Handshake/build identity | exact executable and retained host stability qualified; active PC helper/live startup pending | specimen hash qualified for scoped emulation; not a process handshake | qualified for bounded adapter revision and native build | planned | planned |
| Create game | pending | not applicable | qualified only for clean classic same-save v1 route | unsupported | unsupported |
| Load original save | pending | not applicable | pending qualification | unsupported | unsupported |
| Load supported Rust save | not applicable | not applicable | not applicable | unsupported | unsupported |
| Set/capture RNG state | pending observation | explicit synthetic CRT/small-bound state reproduced; full seeding/capture unqualified | seed 1 and fixed clock requested by bounded runner; RNG capture unavailable | unsupported | unsupported |
| Function trace | pending tooling | selected RNG original instructions emulated; no live trace | pending instrumentation | unsupported | unsupported |
| Detailed match | pending observation | not applicable | pending qualification | unsupported | unsupported |
| Quick result | pending observation | not applicable | pending qualification | unsupported | unsupported |
| Advance day/world | pending observation | not applicable | qualified only to 14-game-day clean same-save endpoint | unsupported | unsupported |
| Inject game command | pending adapter | not applicable | pending adapter | unsupported | unsupported |
| Export semantic state | pending decoder | targeted only, pending | pending decoder | unsupported | unsupported |

Every future capability change requires a backend/build identity, scenario evidence, and the exact supported scope. No adapter may silently fall back to another path.

The original-function column now includes the scoped [Reversal RNG reproduction](REVERSAL.md). It does not inherit Reversal GDI live claims or imply full original-process calibration. No Rust gameplay capability exists yet; lab CLI execution is not rust-native game implementation.
