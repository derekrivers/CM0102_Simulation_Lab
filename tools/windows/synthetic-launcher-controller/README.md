# Synthetic launcher controller policy

This directory begins Stage 2 with pure policy and tests only. It contains no
production entry point, native interop, process creation, filesystem, registry,
environment, token, Job, window, input, capture, clock, randomness, reporting,
or publication implementation. Nothing here can launch the fixture or game.

`ControllerPolicy.cs` treats observations as data supplied by a future,
separately reviewed adapter. Concrete accepted fixture/source/profile and host
artifact identities are frozen. Its reciprocal linked-token and exact duplicate
policies are the narrowest documented UAC relationship hypothesis, but this
increment does not claim that Windows will grant the `CreateProcessAsUserW`
assignment exemption. The later real API call remains an unproven capability;
error 1314 remains a clean failure with no fallback.

State-bound, generation-bound, one-use policy permits drive an owned monotonic
state machine. The fixed
order separates pre-create approval from suspended creation, Job assignment
and a pre-resume approval from the sole resume, both ready captures from input,
and both complete captures from cleanup. UI success, expected tree timeout and
locked refusal have distinct routes, Job limits and cleanup facts. Locked
refusal has no process-capable route. A fact-gated abort route is available
after acquisition begins and requires cleanup plus final input/guard rebinding
before the attempt can terminate as ineligible.

Only `ControllerPolicyTests.cs` has a `Main`. It constructs synthetic fact
objects and must not access ambient host state. No controller executable is
produced or run in this increment.

The exact public policy profile and public/private schemas are in `config/`.
There is deliberately no private instance: no controller image exists to bind.
The private grammar has only fixed identities, scenario ID and four guard path
roles; it has no executable path, command, arguments or shell field. Verify the
canonical duplicate-free ASCII JSON first, then the schema, then the mandatory
post-schema validator. The canonical parser rejects floating-point lexical
forms; the final validator rejects any case-insensitive duplicate or ancestor
overlap among the four guard paths.
Verify the
frozen source, schemas, profile, canonical verifier provenance, entry-point
split, token mutation tests and absence of authority with:

```sh
python3 tools/windows/synthetic-launcher-controller/verify_controller_policy.py self-test
python3 tools/windows/synthetic-launcher-controller/verify_controller_policy.py verify \
  --repo "$PWD" --source-commit "$(git rev-parse HEAD)"
```

The only Windows output permitted for this increment is the console policy-test
assembly. Build it with the qualified in-box x86 Framework compiler, explicit
`mscorlib.dll` and `System.dll` references under `/nostdlib+`, then require exact
stdout `PASS 2601`. Do not build or run a production controller, fixture or game.
