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
Independent coordinator review accepted exact driver/observer revision
`e36b51604a36c00e52e0c031d250cd8f3458846c` before native compile/relink or
execution and independently repeated the eight controls. Review first found
and fixed closed-stream hangs, incomplete sparse-state admission and missing
per-arm drift checks. No original process was launched.

## Fresh result

The [sanitized receipt](evidence/pc-r5-capture-v1.json) binds one fresh immutable
private build and capture campaign. The separate derivative's executable hash
is `2f471fb8c5b87f69cf51d5423e6ec4e92e95386ba33fda2b1827d01df7781451`;
the retained qualified binary is unchanged. Only the observer was compiled;
existing sealed objects were relinked. The complete campaign's contemporaneous
before/after seals span 339.91 seconds, with four serial native runs taking
83.12, 83.77, 83.56 and 83.25 seconds.

All four runs reached the 14-day endpoint, had positive idle counts and stable
per-arm/global identities. Their 18,975,625-byte saves are exactly identical:
`8e3a60abb32ae8864e32052de34aa2fea00f1709ef54531220e949eb0ba16f11`.
Enabled A and B each produced the same complete 3,849,184-byte sparse capture:
`014808018f7b20f60abaac5c71a0c509747259e309563650afe0d0cc79da6f40`.
All sixteen captured ranges match byte for byte; no field mask or tolerance
was used. Both enabled logs contain one completed-capture marker; disabled
arms contain none. Four of four admitted arms succeeded; two of two enabled
captures are complete. This was one focused setup attempt, with no failed
attempt removed from the denominator.

Independent R4 parsing found one real reciprocal human-manager binding and
sixteen complete registry rows. Fresh guard bytes are zero, allowing the
connected original getter's registry-mutating branch directly, without the
older capture's guard-priming step. R4's [independently parsed official-instruction oracle](PC_R4_HUMAN_REGISTRY.md#fresh-pinned-platform-sparse-replay) passes 21 calls across 290 original instruction starts, with no stubbed
callees, ordered writes/ABI/continuation checks and complete captured-region
plus official-image invariants. Its separate receipt SHA-256 is
`39915e94bf65ca7c6586153dffa63b03160dc483119a58e8dc9e82fbc92fd911`.
This links the fresh input to scoped original instructions; it does not
establish original-process parity or admit a production fixture fingerprint.

The enabled/disabled save equality supports noninterference at this bounded
14-day save endpoint. It does not prove equality of every live byte or prove
which clean data files were opened. The explicit consumption gap remains
`unknown`. Execution, capture completeness, exact raw repetition, scoped
noninterference and original instruction replay remain separate claims.

The final delivery trims the driver's console summary to exclude the private
artifact inventory and normalizes one trailing CRLF in the observer source.
Final diff review caught that formatting warning before merge; the complete
delivery diff was rechecked after normalization. The executed driver remains the exact reviewed revision
`e36b516`, whose file identity is in the receipt. Raw captures, saves,
commands, logs, native pointers, record names, full input tables and build
locators remain in the external private area. Public output contains structural
counts, artifact identities and scoped outcomes only.

Coordinator independently verified the actual private/public artifact identities,
all four before/after seal intervals and output hashes, the executed driver's Git
blob identity, and the fresh original oracle's build/capture link. All checks
passed. The branch refreshed onto the R4 merge and repeated the eight affected
controls. Delivery [PR #36](https://github.com/derekrivers/CM0102_Simulation_Lab/pull/36)
records independent exact-final-head review, all four frozen checks and merge
disposition. This does not rerun or relabel the already sealed experiment.
