# Original host qualification probe

This directory contains the read-only Windows probe defined by
`docs/architecture/ORIGINAL_HOST_QUALIFICATION_V1.md`. It is not a game
launcher. Do not add or pass a game executable path, and do not run the probe
from an unreviewed revision.

Build with the in-box 32-bit .NET Framework compiler. The `x86` target is a
contract requirement because the probe must inspect the same registry view as
the original PE32 executable.

```bat
set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
%CSC% /nologo /noconfig /warnaserror+ /optimize+ /platform:x86 /target:exe /r:System.dll /r:System.Core.dll /r:System.Drawing.dll /r:System.Security.dll /r:System.Web.Extensions.dll /r:System.Windows.Forms.dll /out:OriginalHostQualification.exe CanonicalJson.cs OriginalHostQualification.cs
%CSC% /nologo /noconfig /warnaserror+ /optimize+ /platform:x86 /target:exe /main:Cm0102.OriginalHostQualification.OriginalHostQualificationTests /r:System.dll /r:System.Core.dll /r:System.Drawing.dll /r:System.Security.dll /r:System.Web.Extensions.dll /r:System.Windows.Forms.dll /out:OriginalHostQualificationTests.exe CanonicalJson.cs OriginalHostQualification.cs OriginalHostQualificationTests.cs
OriginalHostQualificationTests.exe
```

Synthetic tests may build in a private temporary directory, not in the
repository. The private locator is strict JSON with exactly these fields:

```json
{
  "schema_version": 1,
  "clean_tree": "C:\\absolute\\clean-tree",
  "clean_manifest": "C:\\absolute\\clean-manifest.tsv",
  "installed_tree": "C:\\absolute\\installed-tree",
  "virtual_store_tree": "C:\\absolute\\virtual-store-tree",
  "iso_file": "C:\\absolute\\CM0102.iso",
  "optical_root": "D:\\"
}
```

The six normalized paths must be distinct. Keep this locator and all captured
output outside Git. Do not invoke the production probe by hand for retained
evidence. From WSL, use the versioned harness after the exact source revision
has passed independent review:

```sh
python3 tools/windows/original-host-qualification/retained_run_v1.py run \
  --repo /absolute/repository \
  --source-commit <40-lowercase-hex-commit> \
  --compiler /mnt/c/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe \
  --expectations /absolute/repository/config/original-host-qualification-v1.json \
  --private-locator /outside-git/private-locator.json \
  --retained-dir /outside-git/new-retained-run-directory
```

The expectations argument must resolve to the canonical repository file, whose
exact bytes must equal that path in the named commit. The compiler must resolve
exactly to
`C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe` and match the
size/hash committed in those expectations. The harness copies those verified
compiler bytes and the exact `1033\cscui.dll` companion into its private build
directory and executes that snapshot. Both identities must match the committed
expectations.

The build uses `/noconfig`, so an adjacent, unbound `csc.rsp` cannot alter the
compiler invocation. Framework references use their absolute in-box x86
Framework paths. Compiler and probe execution use the private build directory
as the fixed working directory and inherit an empty environment.

The destination must not exist, and its existing parent must be owned by the
invoking WSL uid with mode `0700`. A normal DrvFS mount that ignores Unix modes
is rejected; use a metadata-enabled DrvFS view when the capture must reside on
`C:`. Before creating it, the harness parses the
locator, maps every Windows locator path into WSL, resolves existing objects or
the nearest parent of a missing object, and rejects containment or aliases in
either direction with the repository or any locator object. Creation is
relative to a held no-follow parent handle, and the parent and new root remain
held and revalidated. It writes
commit-bound read-only source snapshots into the mode-private build directory,
requires the executing harness and imported verifier to be those canonical
commit-bound repository files, invokes the compiler snapshot and probe directly
without a shell or inherited environment, and enforces
a 30-minute probe timeout and independent 4 MiB stdout/stderr caps. It refuses
identity drift and publishes `retained-run-v1.json` after every strictly
verified full or minimal report whose process exit status agrees with the
report. `verification.qualification_eligible` is separate from verifier
success; unsafe or incomplete evidence remains retained but is never eligible.
The manifest contains hashes and sanitized argument roles, never locator paths
or a game command.

The attempt assumes the invoking account and operating system are not actively
hostile during the run. Concurrent same-account interference invalidates the
evidence; the harness does not claim to defeat swap-and-restore attacks by an
actor with the same account authority.

For independent verification of captured stdout, both the public expectations
and private locator are mandatory:

```sh
python3 tools/windows/original-host-qualification/verify_output.py verify output.json \
  --expectations config/original-host-qualification-v1.json \
  --forbid-file private-locator.json
```

Run the no-launch negative controls with:

```sh
python3 tools/windows/original-host-qualification/verify_output.py self-test
python3 tools/windows/original-host-qualification/retained_run_v1.py self-test
python3 tools/windows/original-host-qualification/verify_output.py static-source \
  tools/windows/original-host-qualification/CanonicalJson.cs \
  tools/windows/original-host-qualification/OriginalHostQualification.cs
```

Exit `0` means only that the host is eligible for a separately reviewed
synthetic-launcher test. It never authorizes direct WSL launch of `cm0102.exe`
and never establishes original behaviour or parity.
