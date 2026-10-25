# PC-R5 current-platform capture

This increment prepares a fresh, private sparse capture on Bosman
`144ed82c248228c7769c6785899527eae5b33c3d`. Historical capture and qualified
baseline executable remain untouched. It does not admit a fixture fingerprint,
claim original-process parity, or extend the production management domain.

The observer is an independently authored linker wrapper around
`f_005cde40`, the existing documented human-turn entry. It observes exactly the
first entry, before the existing host hook, then calls the real hook. It writes
no game memory or RNG state and checks that exposed CPU/FPU structures remain
unchanged. Its host I/O can affect scheduling; that is a limitation to evaluate
through enabled/disabled save comparisons, not a proof from source inspection.

R4's agreed read set is eight global words (counts/table/context/registry
pointers and game date), full club/staff tables, tactical context through
`+0x604`, mapping rows including 32 human alternate rows, both tactical banks,
registry header and up to sixteen full registry rows. Runtime image and heap
high-water bounds admit every pointer before use. Maximum retained payload is
16 MiB. Missing initialization, unsupported pointer or write failure leaves an
incomplete capture. The first attempt is never retried in the same process.

The private sparse format is little-endian `PCR5SP01`, then sixteen records
`u32 virtual_address, u32 byte_count, bytes`, then `PCR5DONE`. It contains
proprietary data and native pointers and must remain outside Git. The completion
footer and host structural validator are both required. The validator independently checks exact global order, every derived extent, count caps and nonoverlapping ranges. The selected human
manager must occupy a reserved staff row and have reciprocal club binding.
The raw data is not an original save or general memory importer.

`scripts/pc_r5_capture.py build` seals pinned clean source/tree, existing native
objects, build metadata, observer, headers, compiler/linker versions and commands,
then compiles only the observer and links a separate binary. Its private output
directory must be new. It does not rerun the generated-code/build graph or
replace the qualified binary. The baseline binary's known digest and existing
objects are retained dependencies; this is a separately identified derivative,
not a claim of a fresh full source build.

The `run` command revalidates source, observer/build receipt, official executable,
all 760 manifest entries and pinned smoke script before execution. It executes
four serial arms: qualified baseline, derivative with observer disabled, enabled
A, enabled B. Each uses fresh private HOME/user directories, classic settings,
seed 1, fixed clock and the same pinned smoke actions with screenshots omitted.
Each must reach the existing 14-day save endpoint. CPU/address-space/file/output
limits and a wall-clock deadline bound each arm. Failed and incomplete results
are retained; a new attempt is required after a failure. Logs, commands,
configuration, raw captures and saves have separate identities.

The native executable is hashed and executed through the same held descriptor.
The `--game` locator is explicit and before/after clean-tree identities are
sealed. Actual game-data opens are not independently observed:
`clean_data_consumption_proven: unknown`. Hashing around execution does not
close that gap. No source patch or instrumentation is silently relabeled as the
qualified baseline. Comparison remains `not-run` in the execution receipt;
four-arm save equality and exact capture-byte equality are separate fields.
No masks or tolerances are used.

Invocation templates (all paths absolute, private output outside Git):

```sh
python3 scripts/pc_r5_capture.py build --source /private/pinned-bosman \
  --build /private/qualified-build --output /private/new-observed-build
python3 scripts/pc_r5_capture.py run --source /private/pinned-bosman \
  --observed /private/new-observed-build --baseline /private/qualified-build/cm0102_recomp \
  --game /private/clean-game --manifest /private/clean.manifest.tsv \
  --output /private/new-capture-attempt
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_pc_r5_capture.py
```

Initial validation: eight redistributable controls cover complete/truncated output,
oversized lengths, unsupported pointers, missing reciprocal human binding,
symlink identity, immutable directory reuse, bounded output, closed-stream hangs, missing extents, overlapping ranges, count caps and timeout.
C11 warning-clean syntax validation passes against the pinned runtime headers.
Build/run awaits independent exact-revision instrumentation review and the
coordinator's heavy-slot allocation. No fresh capture has yet been claimed.
