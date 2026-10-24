# Original Windows host qualification v1

Status: contract and implementation present; two complete retained attempts and a candidate exact stability artifact are recorded. Independent review and merge of the comparator revision remain before the synthetic-launcher prerequisite is accepted.

This probe converts the preliminary Windows observations into reproducible, fail-closed evidence before any original executable launch. It is host research tooling, not game logic, a launcher, original behaviour evidence, or a comparison result.

## Safety boundary

The probe is a 32-bit .NET Framework console program built from reviewed C# source with the in-box x86 compiler. Running as x86 is material: it sees the same registry view as the original PE32 process and can issue the original access request exactly rather than adding a WOW64 selector.

The source and imports must contain no `CreateProcess`, `ShellExecute`, `Process.Start`, game execution, input injection, or registry/file mutation route. No game executable path is accepted. The probe may read files, enumerate processes, duplicate and impersonate a token temporarily, open registry keys for access checks, and write only its canonical standard output/diagnostics through the calling harness. Every handle is closed and impersonation is reverted on all paths.

The bounded attempt assumes the invoking Windows/WSL account, kernel and in-box framework files are not actively hostile during the run. The harness rejects ordinary drift, aliases, cross-account writable capture locations and input mutation, but it does not claim to withstand a malicious same-account actor that can swap and restore executable objects between checks or a compromised operating system. The active account must remain dedicated to the attempt; any concurrent same-account interference invalidates the evidence.

The exact registry access check is `RegOpenKeyExA` against the configured 32-bit key with `samDesired = 0x000f003f` (`KEY_ALL_ACCESS`) and no WOW64 flag. It runs first under the direct WSL-interoperability process token and then under a duplicated active-session Explorer token. It never creates, sets, or deletes a key/value.

## Inputs

The public strict expectations file contains only versioned IDs, expected counts/sizes/hashes, registry key/access expectations, volume expectations, and lexicographically sorted required API/tool IDs. It contains no deployment paths. Each expectations, locator and clean-manifest file is read once into a bounded immutable byte snapshot; parsing and reported identity use that same snapshot.

A private strict locator, retained outside Git, supplies only:

- `clean_tree`
- `clean_manifest`
- `installed_tree`
- `virtual_store_tree`
- `iso_file`
- `optical_root`

Unknown/missing fields, relative paths, aliases, reparse points, case-colliding files, hardlinks, unreadable entries, input mutation during inspection, and identity mismatch fail closed. Locator objects and traversed entries are opened without following reparse points, their filesystem identities/final paths and link counts are checked for containment and distinctness, and handles prevent replacement during inspection. Tree digests include type-tagged directory as well as file rows. The clean manifest's file parents define the exact allowed directory set, so an otherwise invisible extra empty directory is a mismatch. The clean tree is captured twice and both snapshots must match. Raw paths never enter public output.

The calling harness binds hashes for expectations, locator, every source, the exact x86 compiler and its language-resource companion, and the output executable, plus the exact command, source commit, exit status, stderr identity and canonical stdout identity. The executing harness and imported verifier must resolve to the bound canonical repository files; an external copy cannot claim the reviewed source identity. Expectations and locator bytes are each captured once through a descriptor-backed pre-read bound, then those same immutable bytes are parsed, hashed, passed to the probe snapshot and used by the verifier. The harness snapshots the verified compiler files into the private build directory, uses `/noconfig`, absolute in-box framework references, a fixed private working directory and an empty inherited environment, builds outside the repository, and invokes the probe directly through WSL interop with a 30-minute outer timeout, 4 MiB stream caps and mode-private capture. Before creating the destination it maps all locator paths into WSL and rejects containment or filesystem aliasing in either direction. The destination parent must already exist, be owned by the invoking uid and have mode `0700`; creation is relative to a held no-follow parent handle, and parent/root identities remain held and revalidated. It refuses an existing destination and publishes a sanitized canonical run manifest after every strictly verified full or minimal report whose process exit agrees with the report; eligibility is recorded separately, so unsafe and inconclusive attempts remain evidence without qualifying the host. It does not use a `cmd.exe`/PowerShell launch wrapper and does not pass a CM path.

Each retained attempt performs a fresh legacy .NET Framework compilation. That compiler embeds a per-build COFF timestamp and CLI Module MVID, so otherwise equivalent probe images do not have a stable raw SHA-256. Each run still binds its exact image and requires its `probe.executable` and `probe.executable_after` identities to match.

Cross-run stability is a separate, path-free `cm0102-original-host-qualification-stability` v1 artifact, scoped to the exact reviewed `5e6dc7ddd2fe60a4270089c3a1c686c2f90244a1` producer tuple and exact committed public-expectations identity. Before import, the comparator binds the executing verifier to its canonical sibling path and exact reviewed bytes; both comparator and runtime-verifier identities enter the result. It descriptor-walks and holds two non-nested retained roots without following aliases; requires the same Linux mount identity as well as device for both roots and the output parent; rejects multi-link or shared artifact objects; and revalidates every absolute path component, directory, pathname and complete file bytes after capture and around publication. It also requires distinct build/probe command bindings, increasing report/build timestamps and distinct MVIDs. It independently verifies both reports as chronological, complete, 22/22 pass and eligible, then binds each report to its canonical retained manifest, raw probe bytes, source/control snapshots, compiler and compiler companion, expectations, private locator, exit status, stream limits and exact source revision. Command role lists and counts remain closed.

The comparator parses each retained image as i386 PE32/CLI, rejects overlapping header/raw/virtual/CLI metadata layouts and malformed metadata/table headers, and structurally locates the four-byte COFF `TimeDateStamp` and the exact 16-byte GUID-heap entry referenced by the sole Module-table `Mvid`. It zeroes only those two ranges in memory and requires the complete normalized images to be byte-identical. It never modifies or reuses an executed image. Report comparison permits differences only at `/run/observed_at_utc`, `/run/elapsed_ms`, `/probe/executable/sha256`, and `/probe/executable_after/sha256`; the raw image hashes are replaced by the common normalized image hash in the comparison projection. Image byte counts, before/after equality within each run, and every other host, input, token, registry, capability, guard, check and verdict field remain exact. Any missing artifact or fifth difference is rejection, not a tolerance. Publication writes and fsyncs a private temporary file through a held output-parent descriptor, verifies its bytes, and atomically installs the final name without replacement.

## Required observations

Every required check reports `pass`, `fail`, or `error`; a missing check cannot qualify. The probe records:

- real Windows version, architecture, locale/timezone class and bounded display facts;
- active console, current session, input desktop name/state and Explorer presence;
- current and Explorer token SID hash, session, elevation/integrity, administrator state, and sorted privilege IDs;
- current and impersonated-Explorer results for the exact registry all-access request;
- configured registry value hash/equality, numeric-SID/mask ACL and unchanged last-write value;
- clean manifest/tree/executable count, byte and SHA-256 identities plus non-writable checks;
- ISO identity and optical-volume/root executable identity;
- installed and VirtualStore aggregate manifests before and after the probe;
- zero CM01/02 processes before and after; and
- fixed-candidate API/tool availability, resolving `cmd` and PowerShell from the explicit x86 system folder so the x86 probe does not trigger WOW64 path redirection or weaken final-path validation.

Tree summaries expose count, bytes, canonical row digest, hardlink/object-alias counts and mismatch counts only. They never expose relative filenames.

## Canonical output and privacy

Standard output is exactly one UTF-8, no-BOM, minified JSON object followed by LF. Object keys and identifier arrays are lexicographically sorted; numbers are integers. The strict top-level fields are:

- `schema_version`
- `probe`
- `run`
- `host`
- `session`
- `tokens`
- `registry`
- `inputs`
- `guards`
- `capabilities`
- `checks`
- `errors`
- `summary`

The report never contains raw paths, usernames, hostnames, registry Location text, relative filenames, environment values, exception messages, exception type names, or stack traces. Identifiers that must correlate use SHA-256. Before emission, the probe recursively scans every string against all private strings plus slash/escaped variants. A redaction hit emits only the exact minimal inconclusive schema. An otherwise unhandled exception emits that same minimal schema with only a hard-coded operation-stage ID and stable HRESULT category; the stage is not derived from input or exception text. The independent verifier requires the private locator, rejects any other minimal-document shape, and recomputes every required check and final verdict from the observed fields rather than trusting declared outcomes.

The summary always contains `original_execution_status: not-run` and `comparison_verdict: not-run`. Exit status meanings are: `0` complete and eligible only for synthetic-launcher testing; `2` complete but unsafe; `3` incomplete/inconclusive; `64` usage/config failure. It must never describe the host as qualified for original execution.

## Expected decision

The provisional expected result is:

- direct WSL token high/admin and exact access result 0;
- Explorer token medium, same as active console, and exact access result 5 (`ACCESS_DENIED`);
- registry location hash matches the configured installed root;
- clean/ISO/optical identities match;
- input desktop is `Default`;
- no game process, mutation, reparse point, unreadable input, or redaction hit; and
- installed and VirtualStore summaries are unchanged.

Explorer access success, an unexpected registry error, locked/non-default desktop, failed token restoration, running game, input mismatch, or before/after mutation is unsafe or inconclusive—never a pass.

## Acceptance before a live retained probe

The implementation requires no-package console tests plus Linux verifier/static tests for canonical ordering/escaping, strict schemas/configs, redaction injection, deterministic tree summaries, case collisions/reparse/unreadable/mid-read changes, registry-result policy, impersonation restoration, token/session/desktop cases, clean/ISO mismatch, installed/VirtualStore mutation, completeness and static absence of process-launch routes.

Compile and run synthetic tests on the PC first. Independently review the exact source and test revision before the first live probe. Run the live probe twice and require the retained-attempt comparison above, unchanged registry last-write, zero game processes, unchanged installed/VirtualStore summaries, canonical verifier success and retained hashes. Only that later evidence can qualify the host for a separately reviewed synthetic launcher test; it still cannot qualify original behaviour.
