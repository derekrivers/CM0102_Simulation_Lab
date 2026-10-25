# Synthetic launcher runtime

This directory contains the frozen Stage 2 implementation of the synthetic-only
launcher stack.  Stage 2 is deliberately `build-unpinned`: production images
may be compiled and statically inspected, but the shared gate refuses before a
scenario or live-native port can be constructed.  No production image, the UI
fixture, a host probe, `cm0102.exe`, or the game is executed by the retained
builder or by CI.

The sole executable test route is `RuntimeGateTests.exe`; it is compiled only
from `RuntimeCanonicalData.cs`, `RuntimeGate.cs`, and `RuntimeGateTests.cs`.

The five production outputs accept no arguments and have fixed roles:

- `SyntheticLauncherSupervisor.exe` creates only the fixed controller or
  locked-preflight sibling selected by canonical control data;
- `SyntheticLauncherController.exe` contains the fixed UI and timeout routes;
- `SyntheticLauncherLockedPreflight.exe` can publish only worker evidence for
  a locked-desktop refusal and has no process-creation authority;
- `SyntheticLauncherTimeoutFixture.exe` creates only the fixed timeout child;
- `SyntheticLauncherTimeoutChild.exe` waits only.

The UI route has exactly two approved output artifacts:
`SyntheticLauncherReady.v1.bmp` and `SyntheticLauncherComplete.v1.bmp`. Each is
a hand-written 230,454-byte 320 by 240 canonical 24-bit BMP with a positive
height, bottom-up BGR rows, no metadata or trailing bytes, and no row padding.
Their SHA-256 identities are respectively
`4f471fd3bc87f53fef9d7f200eaccb0ebe69a0240a9cf09f79bc2bfec3c51f19` and
`5dac08fba06a53bb0a480fe388907e78147b5c0d042fee53eea2ff81b4ee8bc6`.
They can be emitted only after two independently exact captures of the
corresponding state agree byte-for-byte. Timeout and locked-refusal routes
require both artifact names to remain absent.

`RuntimeCanonicalData.cs` and `RuntimeGate.cs` are P/Invoke-free. The canonical
data source contains the shared scenario plan and execution engine used by both
production adapters and the pure scripted-port tests. Each image has separate
bootstrap and live-native sources, and an image is compiled only with its own
native sources. The bootstrap adapter is read-only and supplies object facts to
the gate. Every scenario/live adapter requires a one-use `RuntimeLeaseUse`; the
current canonical configuration can produce only a one-use `RuntimeRefusalUse`.

The Linux verifier performs source, control-data, inventory, authority-surface,
source-list, and negative-control checks. It deliberately refuses direct file
execution: the retained builder and installed CI invoke a byte-bound copy from
a sealed in-memory file descriptor. The safe local preflight is:

```sh
python3 tools/windows/synthetic-launcher-runtime/retained_build.py self-test
```

The full sealed verifier requires an exact committed `HEAD` and is invoked
automatically by the retained `run` command below; a direct verifier command is
expected to fail its execution-source check.

The retained builder must run from WSL with the already qualified in-box x86
.NET Framework compiler and a fresh directory under a private (`0700`) parent
on the WSL root ext4 filesystem.  It snapshots all inputs, compiles the exact
five production source sets, performs static PE/CLI checks, and runs only the
P/Invoke-free gate test assembly with a 30-second bound:

```sh
python3 tools/windows/synthetic-launcher-runtime/retained_build.py self-test
python3 tools/windows/synthetic-launcher-runtime/retained_build.py run \
  --repo "$PWD" --source-commit "$(git rev-parse HEAD)" \
  --compiler /mnt/c/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe \
  --ui-fixture /absolute/private/SyntheticLauncherFixture.exe \
  --retained-dir /absolute/private/fresh-stage2-directory
python3 tools/windows/synthetic-launcher-runtime/retained_build.py verify \
  --repo "$PWD" --source-commit "$(git rev-parse HEAD)" \
  --compiler /mnt/c/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe \
  --ui-fixture /absolute/private/SyntheticLauncherFixture.exe \
  --retained-dir /absolute/private/fresh-stage2-directory
```

The retained manifest is path-free, includes the candidate production-build
manifest, and records every production image and the accepted UI fixture as
`not-run`, live/original execution as `not-run`,
comparison as `not-run`, and qualification as false.  A later separately
reviewed pinned-control stage may change only the frozen control package and
harness/verifier inputs permitted by the implementation contract; it may not
change these production sources.

Future live worker evidence and the supervisor-composed report bind the two
artifact roles explicitly. The supervisor independently validates the files;
it does not trust the worker's identities. The full report also carries the
fixed scenario-specific completeness, fixture-execution and synthetic-safety
summary. Evidence JSON is minified ASCII-subset UTF-8 with exactly one terminal
LF. A retained live run may publish the accepted report and, for UI success
only, the two approved BMPs; it never retains worker evidence, raw captures,
partial output, or BMPs from timeout or locked-refusal attempts.
