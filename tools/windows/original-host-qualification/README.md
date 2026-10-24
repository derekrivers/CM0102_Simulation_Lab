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
%CSC% /nologo /warnaserror+ /optimize+ /platform:x86 /target:exe /r:System.Web.Extensions.dll /r:System.Windows.Forms.dll /out:OriginalHostQualification.exe CanonicalJson.cs OriginalHostQualification.cs
%CSC% /nologo /warnaserror+ /optimize+ /platform:x86 /target:exe /main:Cm0102.OriginalHostQualification.OriginalHostQualificationTests /r:System.Web.Extensions.dll /r:System.Windows.Forms.dll /out:OriginalHostQualificationTests.exe CanonicalJson.cs OriginalHostQualification.cs OriginalHostQualificationTests.cs
OriginalHostQualificationTests.exe
```

Build in a private temporary directory, not in the repository. The private
locator is strict JSON with exactly these fields:

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
output outside Git. Before a retained run, bind the exact source revision,
source/compiler/executable hashes, public expectations hash, private locator
hash, command, exit status and canonical stdout hash in the calling harness.
Invoke the compiled executable directly, with a 30-minute outer timeout and a
4 MiB stdout cap:

```text
OriginalHostQualification.exe --expectations <public-json> --private-config <private-json> --source-revision <40-lowercase-hex-commit>
```

The public verifier must accept the captured stdout before the result is used:

```sh
python3 tools/windows/original-host-qualification/verify_output.py verify output.json --forbid-file private-locator.json
```

Exit `0` means only that the host is eligible for a separately reviewed
synthetic-launcher test. It never authorizes direct WSL launch of `cm0102.exe`
and never establishes original behaviour or parity.
