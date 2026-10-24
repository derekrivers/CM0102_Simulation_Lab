# Authority-free controller engine

`ControllerEngine.cs` is a pure orchestration increment over the accepted
`ControllerPolicy.cs`. It has no executable entry point, native interop,
filesystem, registry, process, UI, capture, input, reporting, or publication
implementation. Only injected test ports can return the already defined fact
objects. The engine never gives a port a policy permit.

The three entry types fix their routes at construction:

- `UiControllerEngine` accepts only `IUiControllerPort` and the fixed
  `ui-success-v1` route.
- `TimeoutControllerEngine` accepts only `ITimeoutControllerPort` and the
  fixed `tree-timeout-v1` route. It exposes no descendant-creation operation.
- `LockedPreflightEngine` accepts only `ILockedPreflightPort` and the fixed
  `locked-refusal-v1` route. That interface exposes no token, registry,
  environment, process-creation, resume, window, capture, or input operation.

Every forward port call is followed by its matching policy decision and
one-use permit consumption before the next call is lexically reachable. An
exception, rejected fact set, null permit, or rejected state transition stops
all later forward authority and enters one bounded abort pass. The pass attempts
all ten fixed recovery operations independently, even after an exception,
then attempts policy cleanup and one rebind. A recovery, rebind, or terminal
failure is reported only as the fixed `CleanupFailure` category. Exception
types, messages, stacks, paths, handles, pixels, and environment contents never
enter the result. Pixel discard/zeroing occurs before the abort permit, while
registry impersonation restoration and environment-block release are mandatory
cleanup inputs. Sequential or concurrent second `Run` calls are rejected before
another port call.

This remains build-unpinned scaffolding. It does not bind the supervisor,
controller, locked-preflight, timeout-root, timeout-child, runtime profile,
outer Job, scenario-to-image mapping, build manifest, or fixed sibling object
identities required by the accepted runtime contract. No native adapter may be
connected and no production image, fixture UI, probe, original executable, or
game may run on the strength of this increment.

The only executable artifact permitted here is the authority-free console test
assembly built from `ControllerPolicy.cs`, `ControllerEngine.cs`, and
`ControllerEngineTests.cs`. Its exact stdout is `PASS 1235`.

Run the static checks with:

```text
python3 tools/windows/synthetic-launcher-controller/verify_controller_engine.py self-test
python3 tools/windows/synthetic-launcher-controller/verify_controller_engine.py verify --repo /absolute/repository --source-commit FULL_HEAD_COMMIT
```
