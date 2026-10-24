# Authority-free build-unpinned refusal policy

`RuntimeBindingPolicy.cs` models only the exact current state declared by the
5,510-byte public runtime profile at SHA-256
`0f4e98d7fe1c273e3c0b7cf342bae84bcc99a4a5ef16cf087a4fe99d3bb396d1`.
It has no production entry point and reads no files, environment, registry,
clock, process, window, input, network, native, or live Job state. Private
in-memory locks make refusal issuance and acceptance race-safe but confer no
external authority. The facts in this increment are immutable test inputs
checked against constants in the policy; the caller supplies no expected
values.

The only accepted state is deliberately ineligible and unreachable:

- the build binding is `build-unpinned` and its public build-manifest binding is
  unbound, with no claimed manifest identity; this makes no claim that a build
  artifact is physically absent;
- supervisor, controller, locked-preflight, timeout-root, and timeout-child
  identities are unbound; this makes no claim that compiled files are absent;
- the UI fixture alone is `bound-not-run`, at exactly 14,336 bytes and SHA-256
  `f469671fd3d8f4986ced0448a70a023d225ed529802cee63cabb43f6fbca2ad6`;
- no image execution, object observation, or live Job observation occurred;
- live and original execution remain `not-run`, original behavior remains
  unqualified, and process creation remains unreachable;
- the fixed scenario role/name map and outer-Job limits are declarations copied
  from the public profile, not observations that those objects, processes, or
  Jobs exist; and
- object-binding requirements, also declarations rather than observations,
  require the exact public/private configuration and report names, a held exact
  parent, canonical final paths, object IDs, one volume, pairwise-distinct
  regular files, alternate-mount rejection, pairwise-distinct objects,
  single-link files, no reparse points or alternate data streams,
  stable before/after identities, ordinary-copy runtime artifacts rather than
  hardlinks, no executable path in private configuration, and exact rebinding
  before and after use.

Successful validation returns only a `BuildUnpinnedRefusal`, bound to the exact
owner state, scenario, generation, and public profile ID/byte count/SHA-256.
Accepting it once terminally records ineligible and unreachable. It cannot be
transferred or replayed, including when concurrent callers race to accept the
same refusal. This type is not a forward permit, implements no engine
capability, has no conversion to `ControllerEngine` or
`ControllerPolicy`, and is not compiled together with either engine for this
increment.

`RuntimeBindingPolicyTests.cs` rejects mutations of every contract, image,
route, and outer-Job declaration field; nested and top-level nulls; mismatched
identities; and refusal transfer, replay, stale-generation, and null attempts.
One barrier-controlled two-thread case proves that exactly one acceptance
succeeds and that the terminal state remains ineligible and unreachable. The
test uses only explicit `System.Threading.ManualResetEvent`, `Thread`, and
`ThreadStart` threading types. It is the only source here with `Main`. Compile
only these two sources with the reviewed in-box x86 .NET Framework compiler,
explicit `mscorlib.dll` and `System.dll`, and
`/noconfig /nostdlib+ /warnaserror+ /optimize+ /platform:x86`. Require exact
stdout:

```text
PASS 202
```

This increment must not execute or load any supervisor, controller, preflight,
UI fixture, timeout fixture, production probe, original executable, or game.
