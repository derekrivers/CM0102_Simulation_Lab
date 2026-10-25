# Club tactical-plan research view

Rust owns state in one dedicated WASM worker; React submits commands and renders
projections. All squad names and plan labels are fictional. Only the qualified
null-owner, option-zero plan-index setter path is supported. This is not a
reproduction of an original UI handler, a full tactics engine or a playable game.

From the repository root, with the pinned toolchain:

```sh
cargo build -p cm-management --target wasm32-unknown-unknown --release
cargo build -p cm-management --bin management-corpus
cd apps/management
npm ci
npm run build
python3 -m http.server 8766 --directory dist --bind 127.0.0.1
```

Open http://127.0.0.1:8766. Select a plan, apply it, export state, select another
plan, then import the export to restore and continue. Unsupported operations
are unavailable. Imports are bounded and validated before mutation.

`npm run check` needs Playwright and Chromium. Set `PLAYWRIGHT_MODULE` to an
installed Playwright module path and `CHROMIUM_PATH` to an installed browser
when using an existing runtime. The check executes the same corpus natively
and inside a real Chromium WASM worker, then exercises React Apply/Export/Import
and corrupt-import rejection. It writes receipts and a screenshot in ignored
`test-output/`. The accepted contract and evidence are in
`docs/research/PC_R3_MANAGEMENT.md`.
