# Backend capability matrix

Status: initial P00 inventory. `pending` means no qualified local execution supports the capability yet; it is not equivalent to false or unsupported in the upstream project.

| Capability | original-windows | original-function | bosman-native | rust-native | rust-wasm |
|---|---|---|---|---|---|
| Handshake/build identity | exact executable qualified; host constraints observed but retained probe and safe launcher pending | pending capture | qualified for bounded adapter revision and native build | planned | planned |
| Create game | pending | not applicable | qualified only for clean classic same-save v1 route | unsupported | unsupported |
| Load original save | pending | not applicable | pending qualification | unsupported | unsupported |
| Load supported Rust save | not applicable | not applicable | not applicable | unsupported | unsupported |
| Set/capture RNG state | pending observation | pending capture | seed 1 and fixed clock requested by bounded runner; RNG capture unavailable | unsupported | unsupported |
| Function trace | pending tooling | pending capture | pending instrumentation | unsupported | unsupported |
| Detailed match | pending observation | not applicable | pending qualification | unsupported | unsupported |
| Quick result | pending observation | not applicable | pending qualification | unsupported | unsupported |
| Advance day/world | pending observation | not applicable | qualified only to 14-game-day clean same-save endpoint | unsupported | unsupported |
| Inject game command | pending adapter | not applicable | pending adapter | unsupported | unsupported |
| Export semantic state | pending decoder | targeted only, pending | pending decoder | unsupported | unsupported |

Every future capability change requires a backend/build identity, scenario evidence, and the exact supported scope. No adapter may silently fall back to another path.
