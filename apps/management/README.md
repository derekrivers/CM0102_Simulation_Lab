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
npm run preview
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


Use **Load reference clubs** when `REFERENCE_FIXTURE=/private/fixture.json` is
supplied to `npm run preview`, or **Import club fixture** to select the recovered
private JSON file. The loopback-only preview serves it on demand; the private
file stays outside the build directory and is never packaged or committed. The Rust
loader checks its reviewed canonical fingerprint and structural domain before
replacing the world. A separate synthetic-manager fixture is supplied for public
regression checks; its labels and profile explicitly identify it as fictional.

Club switching is a view operation. Applying a plan changes only that club;
the displayed bank/index comes from Rust. Version-2 saves embed the admitted
fixture and preserve commands/deduplication across reload. The previous
version-1 slice format continues to load and re-export byte for byte. Original
game saves remain unsupported.

Accepted changes save automatically in this browser through IndexedDB. Reopening
the same origin recovers the last committed Rust checkpoint. The interface
distinguishes accepted in-memory state from a failed browser save; use **Save in
browser** to retry and **Export state** for a portable copy. A corrupt latest
checkpoint recovers the previous valid checkpoint with a visible notice. A stale
second tab cannot overwrite a newer committed checkpoint; reopen it to recover.
Storage is local to this origin and browser profile; clearing site data removes
it. Keep manual exports for work you need to retain.

`npm run check:storage` runs persistent Chromium/IndexedDB recovery, transaction
abort, corruption, interrupted-write and stale-writer tests. Storage denial and
quota exceptions are injected at the IndexedDB API boundary; this does not claim
actual disk-exhaustion qualification. See `docs/research/PC_R6_BROWSER_STORAGE.md`.

Set `REFERENCE_FIXTURE` to the recovered private fixture path when running
`npm run check` to execute the real-record native/browser corpus too. Test logs
contain only hashes and summaries. Captured-name screenshots and exported state
remain in ignored local test output. Capture provenance and exclusions are in
`docs/research/PC_R3_CAPTURE_INPUT.md` and `MANAGER_BOUND_PLAN.md`.
