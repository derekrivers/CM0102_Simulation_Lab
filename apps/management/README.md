# Club tactical-plan research view

Rust owns state in one dedicated WASM worker; React submits commands and renders
projections. The default squad and all plan labels are fictional. A reviewed private fixture
additionally admits three actual ordinary-club/nonhuman-manager records and
qualified first/second bank resolution. A separately admitted human profile supports
direct registry slot selection; other human-manager workflows remain unavailable. This is not a
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

The separate qualified human profile exposes **Apply slot** only after Rust
admits its fixture. Use **Import club fixture**, or set `HUMAN_REFERENCE_FIXTURE`
to the private projected human fixture and choose **Load human reference**. The
local preview serves that file only on demand and never packages it in `dist`.
Only direct selection of research slot 1/2 on a preinitialized reciprocal
human-manager binding is supported. The original outer tactical getter can
follow a separate fallback; no original UI, appointment, plan decoding or match
effect is claimed. Human state uses an explicit v3 slice save; v1/v2 formats are
unchanged. Browser persistence uses the same exact-save contract for v3.

Set `HUMAN_REFERENCE_FIXTURE` for `npm run check` and `npm run check:storage` to
include the admitted private human fixture. A separately labeled public synthetic
human profile always runs. Fresh capture fingerprints require independent
qualification and are not automatically admitted.

Set `REFERENCE_FIXTURE` to the recovered private fixture path when running
`npm run check` to execute the real-record native/browser corpus too. Test logs
contain only hashes and summaries. Captured-name screenshots and exported state
remain in ignored local test output. Capture provenance and exclusions are in
`docs/research/PC_R3_CAPTURE_INPUT.md` and `MANAGER_BOUND_PLAN.md`.
