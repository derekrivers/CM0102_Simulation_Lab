# LAB-005/006 frozen pilot admission

25 October 2026. Operational code is ready for independent exact-revision review.
This document does not report a pilot or qualification acceptance. The active
qualification and its selected RNG replay retain their checkout, state, launcher,
configuration and heavy-work slot. All commands below use the separate candidate
checkout and private root. No LAB-007 executor is admitted.

## Freeze now without execution

The lead creates a clean native Linux checkout at the independently reviewed
source revision and a new private configuration containing `python`,
`oracle_python`, `original_executable` and `retained_capture`. No build is needed.
Use `/home/derek/cm0102-lab005-006` and
`/home/derek/.local/share/cm0102-lab005-006`; never repoint the active qualification.
The production Python must be 3.12; LAB-006 requires Capstone 5.0.7. Freeze checks
bounded ordinary input files, exact specimen/capture hashes, the clean Git source,
interpreter versions and all relevant module/native-library pins. It hashes inputs
and imports the disassembler solely to read its version; it never decodes original
bytes or runs either retained-input endpoint.

```sh
python3 /home/derek/cm0102-lab005-006/tools/lab/lab.py \
  --root /home/derek/.local/share/cm0102-lab005-006 \
  freeze research-anomalies --campaign lab005-pilot-v1 \
  --out /home/derek/.local/share/cm0102-lab005-006/lab005-frozen.json
python3 /home/derek/cm0102-lab005-006/tools/lab/lab.py \
  --root /home/derek/.local/share/cm0102-lab005-006 \
  freeze research-consumers --campaign lab006-pilot-v1 \
  --out /home/derek/.local/share/cm0102-lab005-006/lab006-frozen.json
```

Each frozen manifest has one fixed job, zero observation horizon, 300 seconds
elapsed, 120 seconds stall, 2 MiB combined output, 64 MiB monitored attempt disk,
1 GiB minimum free space, and at most two physical attempts. The same limits apply
to a single selected-result replay. Stop on one failure or any divergence. A
changed ceiling, job, parameter, source, configuration or pin requires a new freeze
and independent review. The ordinary `start research-anomalies` and
`start research-consumers` commands continue to reject; incomplete qualification
cannot be bypassed by a manifest/configuration approval flag.

Freeze physically allocates **536 MiB per profile**, 1,072 MiB for both profiles:
four physical attempts (pilot plus selected replay, each with one infrastructure
recovery) times 130 MiB (64 MiB attempt disk, 2 MiB output allowance and 64 MiB
sampled-overshoot headroom), plus 16 MiB metadata. Inputs remain in place and are
not copied. `posix_fallocate`, allocated-block verification and a filesystem
free-space check establish the reservation; sparse files do not count. The
reservation is private, outside the monitored attempt trees, and its subject hash
binds it to the frozen source/configuration/job/limits. Only the worker holding
the existing global heavy lock releases one allocation per immutable attempt.
A journal-before-truncate transition is restart-idempotent. At most one pilot
and one replay campaign may consume it. Unused allocations remain for recovery
and replay. The existing disk watchdog is sampled, so this reserve covers the
declared worst-case budgets plus explicit headroom; it is not a hard filesystem
quota or a promise against unrelated processes exhausting the filesystem.

## Independent review and qualification receipts

The reviewer inspects the exact source, actual frozen manifest, source/input/tool
identities, controls and physical allocation, then retains a private JSON receipt:

```json
{
  "schema_version": 1,
  "kind": "research-operational-review-v1",
  "decision": "approved-for-pilot",
  "reviewer": "independent reviewer identity",
  "implementation_author": "implementation author identity",
  "source_revision": "exact 40-character reviewed source revision",
  "campaign_id": "lab005-pilot-v1",
  "frozen_subject_sha256": "exact subject hash printed by freeze"
}
```

The subject is canonical manifest JSON excluding `campaign_id` and the later
`pilot_admission`/`replay_of` provenance fields. The review separately binds the
original campaign ID. This avoids a source/receipt/manifest hash cycle while
binding all scientific and operational inputs. The admitted manifest includes
the receipt's absolute path and SHA-256. Selected replay retains that receipt and
must link to the exact admitted original manifest hash and job. It cannot alter
its source, configuration, inputs, tools, job or limits.

Qualification acceptance must follow
[the LL1 closure procedure](LL1_QUALIFICATION_ACCEPTANCE_V1.md). The validator
requires the exact qualification ID/source/manifest, completed 86,400-second
eligible horizon after its actual start, all three successful endpoints, complete
original/replay inventories and canonical publications, unchanged configuration
and source/tool/input pins, and the separately completed post-horizon RNG replay.
The actual native/WASM files must each contain 75,952 bytes with the frozen RNG
digest and `[1023,61,2447,123]` controls. Terminal report and snapshot must match.
The acceptance timestamp must follow replay completion. Interim, failed, censored
and self-reviewed receipts reject. A reconciled historical publication error is
not silently ignored: the final independent qualification review must disposition
it; all current publications and full inventories still must verify.

These are independently authored attestations within the local operator trust
boundary, not digital signatures or cryptographic proof of a person's identity.
The implementation does not generate approval receipts. A `passed` field alone
cannot satisfy the source, chronology, raw-artifact and endpoint checks.

## Controlled admission and sequential launch after acceptance

After actual qualification completion and independent selected-RNG-replay
acceptance, run the following once for each corresponding manifest and review:

```sh
python3 /home/derek/cm0102-lab005-006/tools/lab/lab.py \
  --root /home/derek/.local/share/cm0102-lab005-006 \
  admit /home/derek/.local/share/cm0102-lab005-006/lab005-frozen.json \
  --operational-review /PRIVATE/lab005-operational-review.json \
  --qualification-acceptance /PRIVATE/qualification-acceptance.json
```

`admit` rechecks the complete pinned evidence and configures a ready campaign. It
does not start a service. The same gates run at worker start, before preparation,
in the isolated workload process and after its endpoint. Existing `core replay`
retains those gates and uses the reserved selected replay allocation. The global
single-worker lock and unchanged systemd CPU/memory/task controls remain mandatory.

Use a **separate Windows launcher directory**, never Setup on the accepted
qualification launcher. After qualification acceptance, install the reviewed
candidate scripts from this checkout using, for example:

```powershell
& '<candidate checkout on Windows>\tools\lab\Lab.ps1' Setup `
  -LauncherDirectory "$env:LOCALAPPDATA\CM0102Lab005006" `
  -Repo '/home/derek/cm0102-lab005-006' `
  -StateRoot '/home/derek/.local/share/cm0102-lab005-006'
& "$env:LOCALAPPDATA\CM0102Lab005006\Lab.cmd" Resume lab005-pilot-v1
```

Installed launchers read their own adjacent `launcher.json`. Resume and Replay
start the existing hidden Windows lifetime holder and require its fresh handshake;
the holder provides a finite system-awake request and attached WSL client. A direct
WSL CLI service launch is not unattended acceptance. Run LAB-005 first, retain and
inspect all results, then allocate LAB-006; selected replays also run sequentially.

Measure actual CPU/memory/disk/stall behaviour and inspect both complete LAB-005
decoder ledgers, every LAB-006 instruction fact, controls, exclusions, failure
denominators and deterministic selected-result replay. Independent raw-evidence
review decides scientific acceptance. Operational source review alone does not
accept findings or authorize LAB-007. Keep PR #48 draft until repository review,
refresh, check and evidence requirements are fulfilled.
