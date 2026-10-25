# Club tactical-plan research view

Rust owns state in one dedicated WASM worker; React submits commands and renders
projections. The default squad and all plan labels are fictional. A reviewed private fixture
additionally admits three actual ordinary-club/nonhuman-manager records and
qualified first/second bank resolution. Human-manager controls stay unavailable. This is not a
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


Use **Load reference clubs** when the private reviewed fixture is staged as
`dist/reference-fixture.json`, or **Import club fixture** to select the recovered
private JSON file. It is never packaged or committed by the build. The Rust
loader checks its reviewed canonical fingerprint and structural domain before
replacing the world. A separate synthetic-manager fixture is supplied for public
regression checks; its labels and profile explicitly identify it as fictional.

Club switching is a view operation. Applying a plan changes only that club;
the displayed bank/index comes from Rust. Version-2 saves embed the admitted
fixture and preserve commands/deduplication across reload. The previous
version-1 slice format continues to load and re-export byte for byte. Original
game saves remain unsupported.

Set `REFERENCE_FIXTURE` to the recovered private fixture path when running
`npm run check` to execute the real-record native/browser corpus too. Test logs
contain only hashes and summaries. Captured-name screenshots and exported state
remain in ignored local test output. Capture provenance and exclusions are in
`docs/research/PC_R3_CAPTURE_INPUT.md` and `MANAGER_BOUND_PLAN.md`.
