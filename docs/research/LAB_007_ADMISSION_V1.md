# LAB-007 operational admission and evidence v1

Status, 27 October 2026: independently reviewed and executed. The corrected
campaign completed all 120 cases in twelve jobs with 114 passed and six censored
cases; its preselected job-012 replay passed and reproduced the full scientific
result exactly. See the [decision and diagnostic boundary](LAB_007_BLOCKERS_V1.md)
and [delivery record](LAB_005_007_DELIVERY_V1.md). This runbook preserves the
reviewed operational contract, not permission to repeat a censored campaign.
LAB-005/006 and LL1 were independently accepted; their immutable private receipts
and raw publications were checked again at admission and each physical attempt.

The experiment is exactly `LAB_007_CASES_V1.json`: 120 cases, twelve consecutive
ten-case jobs, 200 assignments and 120 final reads. Every failed, censored,
interrupted and unstarted case/call stays in its original denominator. One
selected replay is frozen now: `012-retained-assignment`, ten cases and 27 calls
at the upper end of the slot range. Its results are reported separately from
the original 120 cases. No reranking or substitute selected job is allowed.

## Scientific boundary

The adapter uses the unchanged R10 model: official PE sections and headers,
seven admitted captured globals, complete retained heap, and a synthetic ABI
stack/return mapping. It does **not** overlay the full captured image or claim
original-process CPU/RNG state. Both exact staff/player hash pairs must equal
the accepted R10 identity receipt. Mode/cache remain zero. Only the selected
slot and the assignment/repeat/replacement sequence vary. The LAB-006 caller's
signed sixteen-iteration loop remains distinct from this direct twenty-slot
experiment; neither twenty UI positions nor additional member eligibility is
claimed. No original Windows process is launched.

Before every case all mapped bytes, including image/heap page padding, stack
and return mapping, are restored from the initial admitted baseline. Full
Unicorn CPU context is restored, then every mapped byte and the complete raw
reused context are compared exactly. No lineup byte is patched into an input.
The same fixed instruction starts, call targets and read fields from R10 apply;
only the selected mapping DWORD is relocated to the case's frozen slot.
Explicit memory operands are checked at the instruction boundary before they
can read or write. Actual code/read/write/invalid-memory hooks retain ordered
facts and stop on the first unsupported dependency. Unsupported boundaries
are censored, never converted into invented rejection semantics.

After each returned call, every mapped region outside the ABI stack must equal
the initial baseline plus exactly the intended four-byte member ID at the
selected slot. Expected region hashes derive from those baseline bytes and the
fixed intended write, not from the observed state. Stack effects and all CPU
state remain completely retained. ABI evidence includes entry arguments,
receiver, return PC, expected/observed ESP/EAX and callee-saved registers.
No-RNG-path evidence is the restricted instruction/call/read/write trace plus
complete mapped-memory invariance; it is not a claim about unobserved original
process RNG state. Defective return/ABI/RNG/effect/width/member/slot/PC/untouched
models must fail. Synthetic tests additionally alter actual padding, mapping
permissions, CPU EFLAGS/XMM state and reconstruction bytes.

## Lossless private representation

Each attempt retains immutable `base-N.bin` for **every** mapped extent and a
`base.json` inventory with addresses, extents, permissions and SHA-256. Every
case reset and each call's actual entry/exit state retain all changed 4096-byte
pages relative to that immutable baseline, ordered extents and complete region
hashes. Reconstruction rejects missing, overlapping, duplicate or reordered
pages, unused delta bytes and mismatched region/context hashes. Raw 5608-byte
CPU context files are retained for every state; reconstruction is independently
usable through `scripts/lab007.py::reconstruct` without executing instructions.

The exact pinned Unicorn 2.1.4 Linux x64 CPU-only `uc_context` layout is grounded
in [uc_priv.h](https://github.com/unicorn-engine/unicorn/blob/2.1.4/include/uc_priv.h)
and [uc.c](https://github.com/unicorn-engine/unicorn/blob/2.1.4/uc.c). The scientific
CPU identity includes context size, mode, architecture, snapshot level, the
required null FlatView, and **all 5568 CPU payload bytes**. Only bytes 20 through
31 are excluded from cross-process comparison: inactive CPU-only memory flag,
C padding and host RAMBlock pointer. No CPU field is masked. Strict version,
64-bit host ABI, 5608-byte context size, CPU-only snapshot level zero and null
FlatView assertions fail closed. Full raw contexts remain in the artifact
inventory and same-instance reset comparison uses every byte without exclusions.

`lab007-scientific.json` retains deterministic complete mapping/CPU identities,
case/call outcomes, ordered effects/traces, controls and boundary facts. Selected
replay requires this file byte-identical. Raw allocation metadata may differ only
at the explicitly documented context-header offsets; reviewers independently
reconstruct every recorded memory state and verify the full CPU payload.

An initial durable checkpoint publishes all ten planned cases and every planned
call before input loading. Actual entry states are recorded after ABI setup and
before emulation. Each call has a durable append-only event trace; completed
calls and cases publish immutable receipts and refresh the durable checkpoint.
Every event is flushed to the OS; each sixteen-event prefix and each boundary
or call completion is fsynced. An atomically published trace durability receipt
then gives the exact sequence, byte length and hash of that committed prefix.
The main checkpoint follows the file publications; its atomic replacement and
parent-directory fsync commit the whole bundle before case progress advances.
Trace instruction/write events describe pre-execution
observations, so even the last durable event may precede its instruction's
effect. The last acknowledged durable prefix can lag by one sixteen-event batch,
including the sixteenth event while its flush or durability-receipt publication
is in flight. Power loss can lose that uncommitted suffix. Neither prefix is
asserted to reconstruct an interrupted final state. This wording clarifies the
fixed execution revision's batching behavior; it does not change its adapter.
First-boundary results retain full entry/exit state, PC, missing dependency and
partial effects. If the host/process disappears mid-instruction, the last
checkpoint and trace remain; unavailable final CPU/memory state is explicitly
unknown, not reconstructed by assertion. Recovery creates a separate immutable
physical attempt and restarts its exact ten-case job from baseline. Both attempts
remain in accounting; no partial attempt is silently substituted by a retry.

## Resource and admission contract

Per-attempt limits remain 600 seconds elapsed, 120 seconds without case progress,
2 MiB streams, 512 MiB artifacts, two attempts only for infrastructure recovery,
one CPU, 2 GiB memory, zero swap and 128 tasks. Each call retains the
3,000-instruction ceiling and has a 2,000,000-microsecond emulator deadline.
This explicitly reviewed LAB-007 instrumentation allowance replaces R10's
100,000-microsecond deadline: an invented 301-instruction/150-memory-read path
with per-event fsync was censored at both 100 ms and 2 seconds. Both exact failing
sources and outputs are retained privately. The final sixteen-event prefix
checkpoint policy is measured with the same invented instruction stream and
retains complete traces at normal/censored endpoints. The instruction/state
domain and outer attempt limits are unchanged. There are at most 24 original
physical attempts plus two for the fixed selected replay. Reserve physically
**15,044 MiB**: 26 × (512 MiB artifacts + 2 MiB streams + 64 MiB sampled-overshoot
margin) + 16 MiB metadata. The 1 GiB free-space floor is additional. Reservation
checks allocated blocks as well as logical length, journals consumption before
shrinking the reserve and prevents duplicate job/ordinal consumption and a
second replay campaign. The journal and original artifacts remain private.
The reserve is growth accounting with a watchdog, not a filesystem quota.
The coordinator also checks free host disk backing the WSL virtual disk before
materialization; Linux's virtual capacity alone is not a host-space guarantee.

Freeze hashes only private inputs and pinned source/tools; it never invokes
original instructions. The exact source checkout must be clean. Original
executable, retained image/heap, Python interpreters, venv configuration and all
Unicorn/Capstone Python/native files are pinned. Tool versions must be Python
3.12, Unicorn 2.1.4 and Capstone 5.0.7. The independent operational receipt binds
source revision and full frozen subject; it is external to the source/manifest
to avoid a circular review hash. Admission additionally requires the real LL1
qualification/replay acceptance and exact accepted LAB-005/006 receipt digest,
verifying their complete immutable raw publications. Receipts are independent
attestations in the local trust boundary, not cryptographic identity proofs.

## Supported sequence

The commands below retain the original v1 admission procedure for provenance.
That campaign failed before input loading. Its source/root remain preserved.
The reviewed replacement used source `152de802baa0d88fdfec2f1db153df492d90f955`
in `/home/derek/cm0102-lab007-r2`, private state
`/home/derek/.local/share/cm0102-lab007-r2`, campaign `lab007-matrix-v2` and
isolated Windows launcher `%LOCALAPPDATA%/CM0102Lab007R2`. Its frozen subject is
`a0ddd15261a8d6c72718161e5cb33dcc7c0cd26747ca3cdcf44aeb9527dfa30b`.
The [replacement operational review](evidence/lab007-operational-review-v2.json)
binds the actual materialized pins and physical reservation. Do not run these
commands again against either retained campaign.

The lead creates clean detached `/home/derek/cm0102-lab007` at the independently
reviewed source revision. Development stays in `/home/derek/cm0102-lab007-dev`.
Use private state `/home/derek/.local/share/cm0102-lab007`, whose minimal existing
four-key configuration supplies the two Python interpreters, original executable
and retained capture. Qualification and LAB-005/006 sources, roots and launchers
are preserved. Use an isolated Windows launcher `%LOCALAPPDATA%/CM0102Lab007`
through `tools/lab/Lab.ps1 -Action Setup -LauncherDirectory` with the fixed
repository and state-root arguments (see the local-lab runbook).

From the fixed native checkout:

```sh
python3 tools/lab/lab.py --root /home/derek/.local/share/cm0102-lab007 freeze research-assignment --campaign lab007-matrix-v1 --out /home/derek/.local/share/cm0102-lab007/frozen.json
python3 tools/lab/lab.py --root /home/derek/.local/share/cm0102-lab007 admit /home/derek/.local/share/cm0102-lab007/frozen.json --operational-review /home/derek/.local/share/cm0102-lab007/operational-review.json --qualification-acceptance /home/derek/.local/share/cm0102-lab005-006/qualification/qualification-acceptance-v1.json --precursor-acceptance /home/derek/.local/share/cm0102-lab005-006/reviews/lab005-006-acceptance-v1.json
```

The reviewer checks the actual frozen pins and physical reserve, then writes
the external operational receipt; `admit` configures without launching. The lead
uses isolated Windows `Lab.cmd Resume lab007-matrix-v1` so the lifetime holder
owns unattended WSL execution. Once terminal, retain all twelve jobs and all
physical attempts, then `Lab.cmd Replay 012-retained-assignment -Campaign
lab007-matrix-v1` using the documented launcher argument syntax. Core replay
preserves original limits and pins while selecting exactly the last job.
Independent raw review must decide passed, failed or censored for the full
denominator before any scientific acceptance or further expansion. No worker
can write acceptance receipts, promote production rules or modify Git.
