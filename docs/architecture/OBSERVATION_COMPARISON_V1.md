# Observation comparison v1

Status: comparator mechanics implemented; no real original/Bosman observation bundle has yet been compared.

The execution replay manifest proves which bounded process ran and which request, protocol stream, diagnostics, inputs, limits, and endpoint were retained. It deliberately leaves `comparison_verdict` as `not-run`. It has no game-state observation schema, semantic scope, completeness counters, or comparable original-backend artifact, so execution hashes cannot be promoted into a behavioural verdict.

Version 1 adds two producer-neutral sidecars without changing the replay manifest:

- an observation bundle beside each successful attempt, binding its replay manifest, comparison key, capture completeness, raw artifact, and semantic artifact; and
- a separate immutable comparison attempt containing a canonical request, report, and manifest.

This is the bridge for later original and Bosman adapters. The current implementation qualifies synthetic comparator controls only. It does not complete B2/P02, prove original/Bosman parity, or call a selected semantic projection the whole game state.

## Command and request

```sh
lab-cli compare-observations \
  --request comparison-request.json \
  --left-bundle left/observation-bundle.json \
  --right-bundle right/observation-bundle.json \
  --output-dir new-comparison-attempt
```

The strict request has schema version 1, a safe comparison ID, the 40-hex comparator source revision and expected comparator executable SHA-256, the byte count and SHA-256 of both bundle files, and this fixed policy shape:

```json
{
  "id": "exact-observation-v1",
  "raw_mode": "exact",
  "semantic_mode": "exact-json"
}
```

`raw_mode` may instead be `retain-only`. No masks, ignored paths, tolerances, or alternative semantic modes exist in v1. The comparator hashes its own running executable before creating output and rejects an identity mismatch.

## Observation bundle

The strict, 1 MiB-bounded bundle contains:

- a hashed basename reference to the successful schema-v1 replay manifest;
- a comparison key: scenario and profile IDs; scenario, baseline-data, fixture, logical-command-stream, RNG-policy and clock-policy SHA-256 values; observation-schema ID/version/SHA-256; and semantic-scope SHA-256;
- capture status (`complete` or `incomplete`), truncation flag, dropped-record count, and unparsed-byte count; and
- hashed basename references with media types for one raw artifact and one semantic artifact.

Referenced paths must be single safe basenames. Symlinks and non-regular files are rejected. Each file is opened without following a final symlink, then size and SHA-256 are verified from the same handle or bytes used for comparison/parsing. The linked replay must report schema 1, `succeeded`, `completed-target`, and `comparison_verdict: not-run`; its scenario/profile and retained request/stdout/stderr identities are revalidated.

The semantic artifact is strict JSON:

```json
{
  "schema_version": 1,
  "schema_id": "state-v1",
  "scope_sha256": "<64 hex>",
  "state": {}
}
```

Its schema and scope must match the bundle. State must be an object. Duplicate keys, floating-point JSON numbers, unknown top-level fields, and excessive size/depth are invalid evidence. Integer values, strings, booleans, nulls, ordered arrays, and all object fields are compared exactly. Floating-point observations require a future explicit typed/bit representation rather than an implicit JSON tolerance.

## Verdicts

Validation failures are command failures and publish no scientific verdict. Valid inputs return success for all four verdicts:

1. `inconclusive` if either capture is incomplete, truncated, or dropped any record;
2. `not-comparable` if any comparison-key field differs;
3. `different` if semantic values differ, or if exact raw comparison differs; and
4. `equal` otherwise.

Semantic differences have an exact total count and at most the first 64 deterministic samples. Samples contain JSON Pointer and difference kind only; they never expose values. Raw comparison records equal/different identity and the first differing offset without exposing bytes.

With `raw_mode: exact`, the verdict scope is `raw-and-semantic-exact`. With `retain-only`, the raw identity relation and first difference remain visible but raw bytes do not determine the verdict; an `equal` result is explicitly scoped to `semantic-exact`. Each side's unparsed-byte count remains visible.

## Published evidence and controls

A new mode-0700 output directory atomically receives mode-0600 `comparison-request.json`, `comparison-report.json`, and `comparison-manifest.json`. The manifest binds the canonical request and report plus comparator identity. No host paths are serialized, and identical logical inputs produce byte-identical reports.

Executable tests cover exact A/A equality, raw byte and length changes, numeric semantic mutation, event reordering, omitted RNG state, semantic-only raw retention, incompatible keys, dropped capture, artifact corruption, symlink rejection, forbidden floats/policy fields, existing-output refusal, path redaction, and report stability. These falsification controls qualify the comparator mechanism; real backend observation production and the P02 replay corpus remain separate gates.
