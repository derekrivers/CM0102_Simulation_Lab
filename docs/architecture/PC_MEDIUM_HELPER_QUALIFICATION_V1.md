# PC medium-integrity helper qualification v1

Status: active replacement contract for the next Windows execution increment.
It supersedes the unmerged Stage 3 pinned-control route. The earlier merged
host-probe, synthetic-fixture, authority-free policy, runtime, route-engine,
and build-binding records remain valid historical evidence; none of their
production images or the fixture UI has run. This contract does not authorize
`cm0102.exe`.

## Purpose and boundary

The PC is the primary build, reference-execution, and experiment machine for
local B2 calibration and the first B3/P04 Rust slice. WSL may compile, inspect,
package, hash, and post-verify artifacts, but it may never directly or
indirectly create the original process. The live authority boundary is a
reviewed x86 Windows helper started manually from Explorer under the active
user's ordinary medium-integrity token.

The VPS durable queue, 24-hour pilot, resource changes, and continuous
campaigns remain later B4/P01 work. They do not block this contract, B2 local
calibration, or the start of B3. Formal P04 acceptance still requires the
declared P02 evidence.

The route is split into two separately reviewed products:

- `pc-medium-synthetic-v1` may start only the accepted harmless fixture and
  timeout fixture. It contains no original executable name, path, identity,
  flags, data locator, or generic target selector.
- `pc-medium-original-startup-v1` may be designed only after synthetic
  evidence is independently accepted. It is a different fixed-target image,
  package, schema, and contract. Its first route observes bounded startup only
  and cannot claim original behaviour or parity.

Passing one profile never grants authority to the other. No helper is a
general launcher.

## Preserved evidence and reusable controls

The following remain authoritative inputs:

- official 3.9.68 executable: 7,192,576 bytes, SHA-256
  `0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86`;
- clean 760-file manifest SHA-256
  `920cbf75653473d276cd33fbbe7a90553dcd6fff4c0878e848aaca7736dddac6`;
- accepted fixture: 14,336 bytes, SHA-256
  `f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6`;
- accepted ready and complete BMP identities from the frozen fixture profile;
- accepted host-stability artifact: 3,310 bytes, SHA-256
  `96e38bb7932e1acb64aa7c9a33012f3425318b3a8e3aaf7ce98aaf8e1cd27659`;
- exact environment construction, Job limits, input/capture guards, cleanup,
  privacy scanning, no-replace publication, and comparison principles from
  the reviewed synthetic work; and
- the producer-neutral observation comparison contract and qualified Bosman
  build/replay evidence.

Reusable source is copied into a new helper namespace and reviewed as new
code. Historical images are not relabelled or executed. Useful implementation
material includes held-object reads and rebinding, ACL/stream checks, deadline
math, one-use/refusal state, Job creation/query/cleanup, process topology,
fixed environment construction, session/desktop checks, guarded tree
captures, window enumeration, foreground/input-up checks, `SendInput`, client
`BitBlt`, repeat-capture equality, timeout containment, canonical reports, and
privacy-safe publication. The replacement deliberately collapses the old
supervisor/controller authority transfer: each profile has one helper that
directly controls its fixed target.

The old high-integrity route is not a prerequisite. The live helper must not
use Explorer as a token source, duplicate or impersonate its token, adjust a
privilege, or call `CreateProcessAsUserW`. The unmerged native-Python launch
adapter and pinned-control package are superseded. Their schema/comparator
ideas may be reused only through fresh source and review.

## Fixed operator ceremony

The live helper is an x86 .NET Framework Windows-subsystem executable with an
embedded manifest containing:

```xml
<requestedExecutionLevel level="asInvoker" uiAccess="false" />
```

Its live entry point is parameterless. It rejects any command-line argument,
response file, environment option, current-directory selection, file picker,
target override, or unexpected sibling. The operator opens the fresh attempt
folder in Explorer and double-clicks the fixed helper. CI, WSL, SSH,
PowerShell, `cmd.exe`, Task Scheduler, a service, another helper, or a test
runner may not invoke live mode.

The immediate parent matching the active-console shell Explorer is recorded
as an operator-ceremony fact. It is not treated as token authority. The
helper's own held process token, session, window station, thread desktop, and
input desktop are the authority. A parent mismatch fails before target
creation.

The helper may display one fixed consent dialog naming only its profile and a
short accepted digest, and one fixed terminal PASS/FAIL dialog. The consent
dialog is closed before any foreground, input, or capture check. For the
synthetic profile, one manual double-click authorizes exactly one fixed
campaign containing the closed subattempt sequence below. For the later
original profile, it authorizes exactly one fresh startup attempt. Neither is
general permission or a comparison verdict.

## Package and filesystem layout

Every live invocation uses a fresh protected local-NTFS root. Synthetic and
original packages have closed, profile-specific inventories with no shared
live image. The synthetic profile uses a fresh campaign root with fixed
create-new subattempt roots:

```text
campaign-root/
  control/
  private/
  evidence/
  attempts/
    ui-1/
    ui-2/
    timeout/
```

The original profile uses this fixed logical layout:

```text
attempt-root/
  control/
  game/
  private/
  evidence/
```

The helper resolves its package relative to its own held image object, never
from the current directory, registry, `PATH`, a shortcut argument, or a
search. Every root and leaf is held and revalidated. Reparse points,
hardlinks, alternate streams, compression, EFS, case collisions, aliases,
unexpected objects, cross-volume objects, inherited broad write access, and
replacement after checking are rejected. Exact owner/DACL requirements,
inventory limits, byte limits, identities, and fixed relative names are
frozen by the implementation increment before any live run.

The `game` subtree is an ordinary fresh copy. Before an original start it must
match every clean-manifest row and contain no extra object. The held official
image inside that subtree must match the fixed size and digest above. The game
subtree is the explicit working directory. Neither the clean source nor the
user's installed game is modified.

The helper and read-only post-verifier bind the reviewed source revision,
helper image, control data, schemas, fixture or game inventory, accepted prior
evidence, and exact package inventory. Paths alone, branch names, mutable
checkouts, internally asserted digests, or a digest first calculated by the
same live invocation are not trust anchors. Independent review publishes the
accepted package identity before live mode becomes available.

## Medium-token preflight

Before creating any target, the helper proves:

- `TokenElevation` is false;
- integrity RID is exactly medium (`0x2000`);
- elevation type is `TokenElevationTypeDefault` for a standard user or
  `TokenElevationTypeLimited` for a filtered administrator;
- the Administrators SID is not enabled, `TokenUIAccess` is false, and the
  token is not AppContainer;
- no thread impersonation token is present;
- token session, helper session, and active console session are equal;
- the interactive window station is `WinSta0` and both thread and input
  desktops are `Default`;
- the expected user identity matches the accepted host binding; and
- launch-sensitive privileges are absent or disabled and remain disabled,
  including assign-primary-token, increase-quota, impersonate, TCB, debug,
  load-driver, backup, restore, and take-ownership privileges.

The helper may open the active Explorer token for query-only comparison. It
must not duplicate, impersonate, alter, or use that token to create a process.
An elevation prompt, elevated token, RDP/display/session transition, secure or
locked desktop, unexpected privilege, or unverifiable token state records
target execution `not-run` and denies creation.

The session, desktop, display, DPI, token, and process guards are captured
before authority, immediately before every resume, and after cleanup. Any
transition makes the attempt ineligible.

## Registry denial and virtualization

The helper is x86 so its natural registry view matches the PE32 original. Its
manifest disables registry and file virtualization for the helper. Under the
helper's own token it calls `RegOpenKeyExW` for:

`HKLM\Software\Sports Interactive Ltd\Championship Manager 01-02`

with exact `KEY_ALL_ACCESS` (`0x000f003f`) and no WOW64 selector. The only
accepted result is `ERROR_ACCESS_DENIED` (`5`). Success or any other error
aborts before child creation. No key or value is created, set, or deleted.

The attempt snapshots and later rechecks the physical HKLM key/value identity
and last-write value, the corresponding per-user registry VirtualStore route
including exact absence, the file VirtualStore tree, and the installed game
tree. It also records `TokenVirtualizationAllowed` and
`TokenVirtualizationEnabled` without treating an allowed-but-disabled state as
a write capability.

Every suspended child token is opened for the minimum query and
adjust-default access. Before resume the helper requires the same user,
authentication ID, session, medium integrity, non-elevation, UI-access,
AppContainer, and privilege policy. If virtualization is enabled and may be
changed, it sets `TokenVirtualizationEnabled` false with
`SetTokenInformation`; in every case it re-queries and requires false. If that
cannot be proved, the suspended process is terminated and never resumed.
There is no fallback.

The synthetic qualification must exercise this exact child-token and registry
route before an original-capable image can be proposed.

## Process authority and Job containment

The only process-creation API in live code is fixed-target `CreateProcessW`.
`CreateProcessAsUserW`, `CreateProcessWithTokenW`,
`CreateProcessWithLogonW`, `DuplicateTokenEx`, impersonation, privilege
adjustment, shell execution, managed `Process.Start`, command interpreters,
`PATH` lookup, target selectors, and fallback/retry APIs are forbidden.

Before target creation, the helper proves it is not in an ambient Job, then
creates a non-breakaway, kill-on-close target Job with fixed active-process,
per-process memory, Job memory, UI, and time limits. The helper remains outside
that Job and holds its sole non-inheritable handle. It constructs an
`EXTENDED_STARTUPINFO_PRESENT` attribute list whose sole Job entry is that
held target Job and passes it to fixed-target `CreateProcessW`. On the
qualified Windows version, `PROC_THREAD_ATTRIBUTE_JOB_LIST` assigns the new
process to the Job as part of creation, before user code can run. The target is
also created suspended; membership and queried limits are proved before its
single resume. Missing API support, an ambient Job, attribute-list drift, or
failed membership leaves the target unresumed and the subattempt ineligible.

Because the helper is outside the target Job, it can call
`TerminateJobObject`, prove cleanup, publish evidence, and show the final
dialog. If the helper exits or crashes instead, its sole Job handle closes and
kill-on-close contains the target and descendants. No process inherits that
handle.

The fixed helper and target sequence is:

1. authenticate the complete package and fresh attempt root;
2. pass medium-token, session/desktop, registry, tree, and zero-process guards;
3. create only the profile's fixed target suspended and atomically assigned to
   the target Job with `CreateProcessW` and the fixed Job-list attribute;
4. prove target-Job membership before any target code ran;
5. recheck the target token and disable virtualization;
6. resume the target exactly once;
7. observe, drive, and capture only the actions frozen by that profile;
8. close gracefully where specified, otherwise terminate the Job after the
    fixed deadline;
9. prove the target Job empty and zero target/descendant processes at exit,
   plus stable inputs and guards,
    and complete cleanup; and
10. publish canonical evidence create-new/no-replace, then show the terminal
    dialog and exit.

Every target creation supplies a non-null authenticated absolute application
name, fixed working directory, closed Unicode environment,
`bInheritHandles = false`, and `CREATE_SUSPENDED |
EXTENDED_STARTUPINFO_PRESENT` with the one fixed Job-list attribute. The
synthetic profiles use a null command line. A later original-only profile may
use only one exact reviewed command-line buffer containing the authenticated
application name and fixed flags; it accepts no variable argument. No route
sets a breakaway flag. Standard handles are not inherited. No diagnostic
direct launch, same-subattempt retry, resume, or alternate API is allowed.

## Synthetic qualification campaign

The first implementation is synthetic-only. It may drive the accepted fixture
using its fixed window protocol, geometry, nonce, real foreground-verified
`SendInput`, client-relative desktop `BitBlt`, repeat captures, and exact
approved ready/complete BMP identities. Unexpected pixels are compared in
memory, zeroed, and discarded. They are never published.

One operator action runs one bounded qualification campaign. A campaign is not
one observation. The helper creates each fixed subattempt root immediately
before that subattempt, never reuses it, and performs complete cleanup and
guard rebinding before advancing. It contains exactly:

- two fresh UI attempts whose approved BMP bytes and canonical evidence agree
  after only exact reviewed per-attempt fields are removed;
- one timeout/process-tree containment attempt using the fixed timeout
  fixture.

Non-live M1 policy, engine, filesystem-model, and mutation tests prove
rejection for an elevated/wrong token model, argument or inventory change,
reused root, registry result other than access denied,
non-Default/transitioned desktop, focus/input interference,
token-virtualization failure, package mutation, missing Job-list support, and
Job assignment failure. The live campaign still rechecks each real condition
and fails closed, but it does not manufacture unsafe host, token, registry, or
package state in order to test rejection.

A single successful UI execution is only smoke. The campaign qualifies the
bounded medium-helper route only after its retained evidence and comparison
are independently verified. It says nothing about the original executable or
game behaviour.

## Separate original-startup increment

No original-specific string or input may enter the synthetic image. After the
synthetic campaign is accepted, a later contract must freeze a separate
original-only helper, exact control/package identity, report/privacy schema,
timeouts, process/window expectations, fixed original flags, and clean-copy
construction. Source/artifact review and synthetic negative testing occur
without original execution.

The first manually authorized original attempt performs a bounded startup
observation only. It initially sends no gameplay input. Fixture-only private
window messages, known pixels, 320x240 geometry, and BMP identities are not
reused as original expectations. Unknown original pixels remain private;
public evidence may contain only reviewed hashes, sizes, counters, enums, and
one-way identities.

The fresh clean copy proves `staged_clean_tree_exact`. Launching the held image
from that tree proves `launched_image_from_clean_tree`. Neither alone proves
which data objects the legacy process consumed. Until a reviewed observation
mechanism, isolated physical registry binding, or equivalent evidence closes
that question, the report must state
`clean_data_consumption_proven: unknown`. Such a startup is useful operational
evidence but cannot support a clean-data behavioural claim.

The first original report keeps `comparison_verdict: not-run` and
`original_behavior_qualified: false`. It does not complete B2. Original A/A,
matching original/Bosman observations, deliberate-divergence detection, and
scoped review are subsequent gates.

## Evidence dimensions and privacy

Execution status and comparison verdict remain independent. Canonical records
include at least:

- `launch_authority_status`: `not-run` or `exercised`;
- `target_execution_status`: `not-run`, `started`, `endpoint-observed`,
  `exited`, `failed`, `timeout-contained`, or `cleanup-unproved`;
- separate fixture and original execution statuses;
- capture and cleanup statuses;
- physical-registry, registry-VirtualStore, file-VirtualStore, installed-tree,
  clean-source, package, and attempt-root stability results;
- `comparison_verdict`, initially `not-run` for each execution;
- `qualification_eligible`; and
- `original_behavior_qualified`, false throughout this contract.

Private paths, usernames, hostnames, SIDs, handles, PIDs, raw tokens, registry
Location text, window titles, environment values, commands, exceptions,
security descriptors, unexpected pixels, and guard snapshots never enter
public output. Reports are canonical, bounded, privacy-scanned, immutable, and
published without replacement. A failure is retained when safe; it is never
rewritten into a pass or removed from the denominator.

## Gates

- **M0 — direction:** this contract and roadmap/status pivot are independently
  reviewed and merged. No live image runs.
- **M1 — synthetic build:** the build-unpinned synthetic helper passes pure
  policy/engine/filesystem-model tests, ABI/static authority checks, an exact
  Windows build, the negative mutation controls defined above, and independent
  source/artifact review. Only test assemblies may execute.
- **M2 — synthetic package:** exact reviewed helper/package identities are
  externally bound and a read-only verifier accepts them. No target runs while
  identities are being established.
- **M3 — fixture campaign:** the operator manually starts one complete
  synthetic campaign from Explorer. Independent verification accepts its two
  UI observations, exact comparison, timeout containment, cleanup, and stable
  guards. The associated non-live M1 negative-control result remains bound to
  the accepted package.
- **M4 — original design:** a separate original-launch contract, helper,
  package, clean-copy route, and report/privacy schema are reviewed and merged
  without original execution.
- **M5 — original startup:** the operator manually authorizes one bounded
  original startup from a fresh exact clean copy. Evidence is independently
  reviewed; clean-data consumption remains unknown unless specifically proved.
- **M6 — B2 calibration:** accepted original A/A and matching original/Bosman
  observation bundles detect an intentional divergence and support a scoped
  calibration result.
- **M7 — first Rust slice:** the relevant Rust slice may begin when local
  calibration is adequate; acceptance requires its declared original-backed
  parity, native/WASM agreement, and supported-state save/reload evidence.

No repository test, CI job, WSL command, SSH session, package constructor, or
review step may cross a live gate. Only the manual Explorer ceremony at the
exact accepted revision can exercise the fixed live profile. Missing evidence,
an unexpected result, cleanup uncertainty, or an unexplained difference is
ineligible or inconclusive, never a pass.
