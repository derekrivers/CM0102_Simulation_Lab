# Synthetic launcher implementation contract v1

Status: frozen Stage 2 implementation contract. The separately reviewed
bootstrap rotation incorporated its reporting clarifications into the
qualification contract and installed the one-use workflow transition. It adds
no execution authority. Production images, the fixture UI, the original
executable and the game remain not run.

## Scope and source boundary

Stage 2 implements the complete future-live synthetic stack behind a gate that
rejects the current `build-unpinned` configuration before any process-creation
or other live native route. Stage 3 may change only control data, schemas,
verifiers, harness controls and pinned identities. It may rebuild unchanged
production sources, but it may not change those production sources.

New implementation sources live under
`tools/windows/synthetic-launcher-runtime/`. The accepted
`synthetic-launcher-controller` directory remains inventory-frozen. The runtime
directory contains five production entry-image sources, shared P/Invoke-free
gate/canonical-data sources, pure gate/fault-test sources, a strict verifier, a
retained no-UI build harness and its documentation. The verifier freezes the
exact source list for each output. Native declarations and native call paths are
image-exclusive; no shared native-method source can grant an image another
image's imports.

The five parameterless entry images are exactly:

- `SyntheticLauncherSupervisor.exe`;
- `SyntheticLauncherController.exe`;
- `SyntheticLauncherLockedPreflight.exe`;
- `SyntheticLauncherTimeoutFixture.exe`; and
- `SyntheticLauncherTimeoutChild.exe`.

Each has exactly one private static `int Main()` and no argument-bearing
entrypoint. None accepts a command, target, executable path, argument list,
shell, environment override, selectable role or original-game input.

## Control-data trust and the build gate

The fixed public and private configuration files are ordinary sibling files in
one fresh protected NTFS attempt directory. Each parameterless image discovers
that directory only by opening its own module image, obtaining and holding its
canonical final-path object, and opening the final parent directory. It opens
only exact fixed leaf names relative to that held parent. The process CWD must
resolve to the same held directory but is never a locator. PATH, environment
values, assembly probing and caller-supplied paths are forbidden. The files'
exact final paths, file IDs, volume, regular-file type, single-link state,
absence of reparse points and alternate streams, protected DACL, stable
before/after identities and pairwise-distinct identities are rebound before
use. The private configuration contains only the declared scenario, source
revision, role-keyed expected identities and four fixed guard-path roles; it
contains no executable path/name, command, arguments or environment override.

The separately reviewed retained/live harness is the trust root for the public
configuration identity. Same-account active interference and a compromised
kernel remain excluded exactly as in the accepted host contract. Directly
starting an image, even with internally consistent replacement configuration,
cannot create eligible evidence.

One least-authority bootstrap-binding role is permitted before the lease. Each
image has an image-exclusive, exact-listed native adapter for that role; native
bootstrap source is not shared between images. Its closed native surface is
limited to self-module discovery and held-parent,
fixed-leaf filesystem, hashing, final-path, file-ID, volume, stream and security
descriptor reads, plus one read-only current-directory query and held directory
open used only for equality with the self-image parent. It cannot create or mutate files and has no process
enumeration/creation, token, Job, registry, input, window, capture, network or
IPC authority. It supplies immutable data to a P/Invoke-free `RuntimeGate`.
Every scenario/live native port, including session/desktop and process-absence
observation in the locked preflight, requires a lease.

`RuntimeGate` parses and validates the exact canonical configuration, bindings
and object facts. In the current `build-unpinned` state it can return only an
owner-, scenario-, generation- and profile-bound terminal refusal. The refusal
is consumed once and no scenario/live native port can be constructed. The
dormant `build-pinned` branch may return a one-use, non-transferable
`PinnedRuntimeLease` only when the canonical public configuration has the exact
externally pinned profile identifier, all of its runtime identity claims are
present and exact, and the private configuration copies those role identities
and matches its public binding. No scenario/native call is reachable before
lease consumption.

The identity dependency graph is one-way and exact:

1. an externally reviewed Stage 2 Git commit fixes the production/shared
   sources and pre-existing non-dependent inputs as separate blobs;
2. those sources and the fixed compiler/reference set produce the five image
   objects, then a candidate *production-build* manifest binds only those
   production source blobs, compiler/references, five outputs, accepted UI
   fixture and pre-existing non-dependent inputs. It excludes itself, the
   pinned public/private configurations, the public exact-const schema, the
   Stage 3 verifier/harness/control commit and every later manifest;
3. the pinned public configuration binds that already-created candidate
   production-build manifest, the image objects, private-schema identity and
   accepted fixed inputs, but omits its own digest, either Git commit, the
   public exact-const schema, verifier and harness;
4. each per-attempt private configuration binds the public configuration and
   exactly copies its role identities, but omits its own digest;
5. a later Stage 3 control commit and external control-package manifest bind the
   candidate production-build manifest, public configuration, public/private
   schemas, verifier and harness. The public configuration never binds this
   downstream package; and
6. the final retained-attempt manifest binds that externally authenticated
   control package and the per-attempt inputs/outputs. It is created last,
   omits its own digest and is authenticated by external retained-evidence
   metadata.

No artifact contains its own digest or a digest cycle. The production gate
checks only the public configuration to candidate-production-manifest binding
and the public/private runtime claims. Compiler, source, schema, verifier,
harness, Git-object and downstream control-package provenance remain external
verifier/harness facts. Production images embed no eventual image,
configuration or manifest hash.

The existing 5,510-byte runtime profile remains an immutable historical
`build-unpinned` input; its `absent` fields are not reinterpreted. Stage 2 adds a
new canonical implementation configuration and schema which truthfully mark the
runtime-private schema, implementation verifier and no-UI harness sources as
present and bound, while recording production images as live-unbound,
`build-unpinned`, live execution `not-run`, process creation unreachable and
qualification ineligible.

The live attempt-directory leaf names are exactly
`SyntheticLauncherBuildManifest.v1.json`,
`SyntheticLauncherController.public.v1.json`,
`SyntheticLauncherController.private.v1.json`,
`SyntheticLauncherWorkerEvidence.v1.json` and
`SyntheticLauncherReport.v1.json`, together with the six fixed synthetic image
names listed by this contract. `cm0102.exe` is guard-only and is forbidden from
the attempt directory. Stage 2 may use repository test-fixture names only
inside the pure test assembly; production images contain no alternate leaf or
fallback lookup.

## Fixed image authority

The supervisor maps `ui-success-v1` and `tree-timeout-v1` only to the fixed
controller sibling and `locked-refusal-v1` only to the fixed preflight sibling.
It has one `CreateProcessW` declaration and call site. It creates that sibling
suspended, with no arguments and `bInheritHandles=false`, after configuring an
unnamed non-inheritable outer Job. It assigns and queries membership before the
only resume and holds the Job until every known process and descendant is gone.

The controller accepts only UI and timeout routes. It has one
`CreateProcessAsUserW` declaration and call site, no alternate API or retry,
and selects only the scenario's fixed target. It explicitly enables
`SeIncreaseQuotaPrivilege` and requires the reciprocal linked-token relationship
or fails closed. Win32 1314 is a fixed failed-capability result.

The timeout root binds `SyntheticLauncherTimeoutChild.exe`, has one
`CreateProcessW` declaration and call site with no arguments, creates only that
sibling and then waits. The timeout child only waits. The locked preflight has
no process-creation, token-duplication, registry, input, capture, window,
environment-block or fixture-launch authority.

For process-absence observation only, the fixed case-insensitive image-name set
is `cm0102.exe`, `SyntheticLauncherSupervisor.exe`,
`SyntheticLauncherController.exe`, `SyntheticLauncherFixture.exe`,
`SyntheticLauncherTimeoutFixture.exe`,
`SyntheticLauncherTimeoutChild.exe` and
`SyntheticLauncherLockedPreflight.exe`. Before supervisor launch all seven
counts must be zero. While running, each observer permits only these exact
counts and bound relationships: before worker launch, supervisor `1` and every
other name `0`; locked observation, supervisor `1` plus preflight `1`; UI before
target, supervisor `1` plus controller `1`, and after creation also UI fixture
`1`; timeout before target, supervisor `1` plus controller `1`, after root
creation also timeout root `1`, and after descendant creation also timeout child
`1`. All names not listed for that stage have count `0`. The expected supervisor
is the worker's exact parent, and each expected descendant has the exact already
bound parent/child relationship. For UI and timeout, descendant cleanup returns
the topology to supervisor `1` plus controller `1`; the controller rebinds,
publishes worker evidence and exits; outer-Job empty proof then leaves supervisor
`1` only. For locked refusal, the preflight publishes worker evidence and exits,
then outer-Job empty proof leaves supervisor `1` only. The supervisor publishes
the final report and exits, after which the harness requires all seven guarded
names to have count `0`.

Every duplicate or unexpected matching PID, and every `cm0102.exe` PID, is a
rejection. The preflight obtains parent/identity facts from the process snapshot
and never opens a process or token handle. Reports contain only fixed
zero/nonzero and expected-topology booleans, never names,
PIDs or other private observations. These names may not be used as a launch
selector.

## Object, ACL and report protocol

Every live directory is local NTFS, newly created and non-reused. Its owner is
the exact active user SID. Its DACL is protected and has exactly two explicit
allow ACEs in this order: `LOCAL SYSTEM` full control, then that exact user full
control. Both directory ACEs carry container- and object-inherit flags and no
inherit-only flag. There are no deny, inherited, object-specific, callback,
unknown or additional ACEs on the root. Child files have exactly the two
corresponding inherited allow ACEs and no explicit or additional ACE. Root and
child objects reject EFS, compression, reparse points, alternate streams and
write-through parent or share routes.

Before creation, the held parent identity/security facts and target absence are
checked. Each object is created once under the protected root, opened without
following aliases and immediately validated through its held handle. Its owner,
DACL, volume, final path, file ID, link count, reparse/stream/compression/EFS
facts remain stable through route-specific before-publication and after-cleanup
rebinds.

Two-party evidence composition is mandatory. Every worker publishes one fixed
`SyntheticLauncherWorkerEvidence.v1.json` with create-new/no-replace semantics.
It contains only facts directly observed by that worker and is not a public or
retained report. The supervisor reopens and validates that exact object and
combines it with only the supervisor facts it directly observed, including the
single create/resume call counts, outer-Job limits, assignment and membership
before resume, wait, termination and Job-empty proof. The supervisor then
publishes the sole public `SyntheticLauncherReport.v1.json` once with
create-new/no-replace semantics. It never represents supervisor facts as
worker-observed or rewrites either object.

The locked preflight creates no attempt tree, BMP, fixture, capture, diagnostic
or arbitrary temporary artifact. Its sole output artifact is the fixed
canonical worker evidence containing only its bound desktop/process refusal
facts; stdout and stderr remain empty. The supervisor validates exit `21`, that
evidence, empty streams, Job cleanup and route-specific guards before composing
the public locked-refusal report. Any other preflight exit, stream byte or
artifact is ineligible. After final-report validation and closure of every
worker-evidence handle, the supervisor deletes the exact bound object without
retention, proves exact-name and object absence, and makes no physical-byte
erasure claim. The
later retained live harness may ordinary-copy only the accepted public report
to its protected retained directory with its own create-new publication. No
report uses stdout or stderr as a data channel.

Exit codes are fixed:

- `0`: scenario-specific accepted worker result;
- `20`: build-unpinned terminal refusal;
- `21`: expected locked-desktop refusal;
- `22`: expected contained tree timeout;
- `30`: binding or safety rejection;
- `31`: native capability failure;
- `32`: cleanup or rebind failure; and
- `33`: report validation or publication failure.

Any other exit is an ineligible capability failure. Stage 2 execution is
limited to pure console tests, so every production-image exit remains
unobserved until the pinned live gate.

## Fixed budgets

All durations use a monotonic clock and are hard upper bounds:

- supervisor total attempt: 120 seconds;
- UI ready/window wait: 30 seconds;
- UI transition wait after the single input: 10 seconds;
- orderly close grace: 5 seconds;
- tree-timeout observation interval: 5 seconds;
- post-termination Job-empty proof: 5 seconds;
- worker-evidence and final-report appearance: 5 seconds each;
- process/Job/window polling interval: 50 milliseconds;
- compiler invocation in the retained no-UI harness: 180 seconds per image;
- pure test assembly: 30 seconds; and
- complete retained no-UI harness: 20 minutes.

Each stdout and stderr stream is capped at 65,536 bytes. A worker-evidence
document and canonical report are each capped at the frozen profile value of
262,144 bytes. A private configuration and public configuration are each capped
at 65,536 bytes. The existing per-process 256 MiB and scenario Job limits remain
unchanged. Timeout, overflow or inability to prove complete process-tree cleanup
fails closed.

## Stage 2 build and evidence

The retained harness uses the reviewed in-box x86 Framework compiler with
`/nologo /noconfig /nostdlib+ /warnaserror+ /optimize+ /debug- /platform:x86`,
explicit framework references, exact source lists, exact `/main`, no response
files and no reference probing. It compiles the five production images and
separate P/Invoke-free pure test assemblies. It accepts the already qualified
14,336-byte UI fixture at SHA-256
`f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6`
as an ordinary-copy input and never rebuilds or starts it.

Only pure console test assemblies may execute. The harness rejects any request
to execute a production output before process creation. Static PE/CLI checks
prove PE32/i386, exact parameterless entrypoints, metadata/call targets and the
per-image import matrix. The retained path-free manifest records every
production image and fixture as `not-run`, live and original execution as
`not-run`, original behavior unqualified, fixture execution `not-run`,
comparison `not-run` and qualification false.

Stage 2 also freezes canonical synthetic pinned public/private configurations,
the worker-evidence grammar and the final full-report grammar as test fixtures.
They contain deterministic placeholder identities that can never match a live
image. Pure tests prove that unchanged production logic rejects every mismatch,
issues a lease for an entirely matching mocked pinned snapshot, and traverses
the complete mocked scenario routes. Stage 3 substitutes only exact real
identity/control bytes and does not change production sources or control-flow
semantics.

The separately reviewed workflow-bootstrap increment updates the installed base
guard, rotates the frozen qualification document/verifier identities, applies
this contract's two-party evidence and timeout/locked sequencing clarifications
to the qualification document, and installs one exact one-use transition from
the bootstrap workflow to the Stage 2 static-verifier/pure-test workflow. The
transition can add only the fixed sealed-verifier and P/Invoke-free pure-test
steps, and only after the verifier and three pure-test inputs already exist on
the reviewed base branch. The guard derives their identities from that trusted
base and requires byte-identical head copies. Thus the Stage 2 implementation
PR adds no workflow diff; after it merges and its files become trusted base
inputs, a separate workflow-only activation PR consumes the transition. After
that activation merges, all workflow changes are rejected again. The Stage 2
workflow executes only P/Invoke-free pure tests and the static verifier, which
rejects P/Invoke, managed process launch, reflection, filesystem, registry,
environment, network and GUI authority in those tests. Production images and
the UI fixture remain compile/static-inspect only and can never be selected by
a CI execution helper.

## Required negative controls

Pure tests and verifier self-tests cover at least:

- unpinned refusal before the first port/native call and refusal transfer,
  replay, stale generation and concurrent consumption;
- every scenario/name/target/argument mapping mutation;
- missing or mismatched self, sibling, manifest, configuration, source,
  compiler/reference, verifier, harness and schema identity;
- aliases, hardlinks, reparse points, alternate streams, EFS, compression,
  alternate mounts, cross-volume objects, overlap, non-NTFS storage, reused
  output, inherited-child-ACE drift and write-through parent/share routes;
- supervisor create/configure/assign/query/resume/timeout/termination/empty and
  crash-window failures, wrong topology and wrong limits;
- controller token/session/integrity/elevation/privilege/relationship failures,
  registry results other than exactly 5, environment drift and API fallback;
- timeout child mapping, argument and call-count drift;
- locked-preflight acquisition or launch authority and unexpected artifacts;
- input, nonce, foreground, window, geometry, DPI, capture, pixel, cleanup,
  guard, report, privacy and publication failures from the qualification
  contract; and
- extra imports, entrypoints, source files, managed launch routes, reflection,
  escaped identifiers, compiler inputs, workflow changes and synchronized
  source/test weakening.

Passing Stage 2 proves only that the complete implementation compiled, its pure
fault model passed and its images satisfied static inspection without being
run. It does not make process creation reachable or qualify a synthetic or
original observation.
