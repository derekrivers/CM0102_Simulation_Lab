# Harmless Windows Forms fixture

This directory contains Stage 1 of the synthetic-launcher qualification gate.
It contains a harmless x86 Windows Forms fixture and static/profile tests only.
It has no launcher, original-executable, game-data, filesystem, registry,
network, clipboard, shell, child-process, standard-output or standard-error
route. Do not add one in this stage.

The fixture accepts no command-line arguments. Before constructing its only
window it requires a medium-integrity, limited, non-administrator token in the
active console session on the `Default` input desktop, and independently
requires the token's elevated flag to be false. Its complete inherited
environment must contain exactly these case-sensitive names:

```text
CM0102_SYNTHETIC_CWD_SHA256
CM0102_SYNTHETIC_INPUT_NONCE
SystemRoot
TEMP
TMP
WINDIR
```

`CM0102_SYNTHETIC_CWD_SHA256` is the lowercase SHA-256 of the exact UTF-16LE
current-directory string. `CM0102_SYNTHETIC_INPUT_NONCE` is exactly eight
lowercase hexadecimal digits and must be nonzero. `SystemRoot` must equal
`WINDIR`, and `TEMP` must equal `TMP`, under ordinal case-insensitive
comparison. This fixture intentionally validates equality but not attempt-root
containment for `TEMP` and `TMP`; the future reviewed controller owns that
path binding and construction of the complete environment block.

The fixed window starts at `(64,64)`, has a `320x240` client, disables automatic
scaling and does not use fonts, images, themes or external assets. It paints
four exact RGB bands. Before querying the screen or constructing the form it
requires `SetProcessDPIAware` to succeed. A transition from `ready` to `complete` requires one real
left-button message at client point `(96,112)` whose `GetMessageExtraInfo`
value equals the configured nonce. Any other mouse-down transitions to
`fault`. The fixture exposes only two fixed query messages:

- `WM_APP + 0x51` (`0x8051`) returns protocol magic `0x434d0101`.
- `WM_APP + 0x52` (`0x8052`) returns `1` ready, `2` complete or `3` fault.

It never closes itself. After a future controller observes and captures the
complete state, that controller must request orderly window closure. Fixture
exit zero means only that it closed after reaching `complete`; it is not a
qualification verdict.

Build only in a private temporary directory with the qualified in-box x86 .NET
Framework compiler. The illustrative compiler commands are:

```bat
set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
%CSC% /nologo /noconfig /warnaserror+ /optimize+ /platform:x86 /target:winexe /r:System.dll /r:System.Core.dll /r:System.Drawing.dll /r:System.Security.dll /r:System.Windows.Forms.dll /out:SyntheticLauncherFixture.exe SyntheticFixture.cs
%CSC% /nologo /noconfig /warnaserror+ /optimize+ /platform:x86 /target:exe /main:Cm0102.SyntheticLauncherQualification.SyntheticFixtureTests /r:System.dll /r:System.Core.dll /r:System.Drawing.dll /r:System.Security.dll /r:System.Windows.Forms.dll /out:SyntheticFixtureTests.exe SyntheticFixture.cs SyntheticFixtureTests.cs
SyntheticFixtureTests.exe
```

Qualification evidence must use the retained harness, not the illustrative
commands. From WSL, choose a fresh destination whose existing parent is private
and mode `0700`; the destination must not already exist:

```sh
python3 tools/windows/synthetic-launcher-qualification/retained_build.py self-test
python3 tools/windows/synthetic-launcher-qualification/retained_build.py run \
  --repo "$PWD" \
  --source-commit "$(git rev-parse HEAD)" \
  --compiler /mnt/c/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe \
  --retained-dir /absolute/private/fresh-retained-directory
python3 tools/windows/synthetic-launcher-qualification/retained_build.py verify \
  --repo "$PWD" \
  --source-commit "$(git rev-parse HEAD)" \
  --compiler /mnt/c/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe \
  --retained-dir /absolute/private/fresh-retained-directory
```

The harness commit-binds and snapshots the sources, profile, verifier, harness,
qualified compiler and compiler companion; binds the absolute x86 Framework
references, exact command roles and minimal environment; validates both outputs
as PE32/i386 CLI images; and runs only `SyntheticFixtureTests.exe` under bounded
stream and time limits. Its canonical path-free manifest records explicitly
that `SyntheticLauncherFixture.exe` was not executed and original execution is
`not-run`. No binary or private retained directory is committed.

The C# test executable exercises pure configuration, token, input and paint
policy. It does not construct the form or call Windows token/desktop APIs.
Linux/static validation is:

```sh
python3 tools/windows/synthetic-launcher-qualification/verify_fixture.py self-test
python3 tools/windows/synthetic-launcher-qualification/verify_fixture.py verify \
  --repo "$PWD" \
  --source-commit "$(git rev-parse HEAD)" \
  --fixture "$PWD/tools/windows/synthetic-launcher-qualification/SyntheticFixture.cs" \
  --tests "$PWD/tools/windows/synthetic-launcher-qualification/SyntheticFixtureTests.cs" \
  --profile "$PWD/config/synthetic-launcher-fixture-v1.json"
```

The canonical public profile binds the exact fixture and test sources as well
as every environment, token, display, geometry, input, protocol, state and
pixel constant. The verifier also freezes both source identities, rejects
symlinked path components, and requires every input plus the verifier itself to
equal its blob at the named full Git commit. Verification rejects a stale,
regenerated, copied, aliased or alternate profile/source set.

Passing these tests authorizes only independent review and later implementation
of a synthetic-only controller. It does not authorize running the original
executable, the production host probe or the game.
