# P02 preliminary Windows reference-host probe

Date: 24 October 2026

Status: two immutable live probe attempts retained and independently verifiable, but host qualification remains inconclusive because both stopped at the same sanitized .NET exception. Launcher implementation and all original behaviour remain pending.

## Evidence boundary

The preliminary observations were collected on 24 October 2026 through bounded WSL and Windows PowerShell/`cmd.exe` inventory commands during the active Codex session. They included OS/session/process inventory, token privilege and integrity queries, registry value/ACL/access probes, tool discovery, filesystem mode/type/count/hash checks, independent Windows executable hashing, mounted-volume inspection, and process absence checks. That preliminary session retained no versioned probe transcript or sanitized output bundle.

The exact host, token, privilege, registry, and tooling statements below remain unverified operational observations because the first two versioned live attempts did not reach a complete report. The versioned [qualification contract](../architecture/ORIGINAL_HOST_QUALIFICATION_V1.md), read-only x86 probe, strict verifier, and bounded retained-run harness freeze the route to durable evidence. Before any original launch, a reviewed diagnostic revision must identify and resolve or explicitly classify the current incomplete stage, then two complete stable attempts must reproduce the observations. Any discrepancy invalidates the provisional launcher assumptions.

## Retained live qualification attempts

The exact reviewed source commit `41599a20f0acc97419ee8a059dae4b9ecf3d11c0` was merged through PR #12 at merge commit `e36004ab84f10cb95f5cb54cf0b5d43b805fb54b`. Two fresh retained attempts used that source, the bound in-box x86 compiler, the exact public expectations, the private clean/installed/ISO locator, a mode-private metadata-enabled destination, and an empty child environment. Both harness invocations returned `PASS`, meaning their canonical minimal reports, process exit status, privacy constraints, and retained bindings verified; it does not mean the host qualified.

Both canonical reports are byte-identical at 603 bytes with SHA-256 `5cf9307ee6bf39b154dff28f674add22893f71fe0d68d741079876486c8d45f9`. Both report exit `3`, `completeness: incomplete`, `safety_verdict: inconclusive`, `qualification_eligible: false`, `cm0102_launched: false`, and the sanitized detail `unhandled-exception-80131501`. Their retained-manifest SHA-256 values are `77bbfcb52a89aabdd65518b46f737df9d4a8e439584f5d64d967d78e5e41d60d` and `7a353164169a910611af782b50c2d2fe96613fec522b2d7459ca2304aa379821`. The manifests differ only in fresh-build-dependent probe executable and command hashes; compiler, compiler resource, expectations, locator, source identities, exit, stream identities, and verification fields agree.

The game was never launched. The repository remained clean after removing verifier bytecode cache, the pinned clean-manifest identity remained `920cbf75653473d276cd33fbbe7a90553dcd6fff4c0878e848aaca7736dddac6`, and no CM01/02 process was present after either attempt. Because a minimal report cannot prove the later installed-tree, VirtualStore, registry-last-write, or token observations, these attempts are durable diagnostic evidence only and do not satisfy host qualification.

Probe/harness version 1.1 was independently reviewed with no findings and merged through PR #13 at exact source `9898e3d933ac21267ea88a58b6f3cad77af8f01c` (merge `da79da6183f943047e7b051e7ce2735f0b3dc374`). A third fresh retained attempt again passed harness and independent output verification without launching the game. Its 633-byte canonical report has SHA-256 `83ba90b6f949bd1c53feb1d77bed361712706df079cd91c56275d069fd634bf0`; its retained manifest has SHA-256 `3f08d3a04d63c422ac64d2a967db8c21771ecb0deac777103e8758d3c7be0e17`. It remained exit `3`, incomplete, inconclusive and ineligible, but safely localized the exception as `unhandled-v1-capabilities-exception-80131501`.

A bounded synthetic capability-only diagnostic then reproduced the failure without accepting private inputs or invoking the probe/game. In the x86 process, `cmd` and PowerShell paths derived from `SpecialFolder.System` were transparently redirected by WOW64, so the reviewed final-path equality guard rejected both with `0x80131501`; all other fixed tool candidates and all five API groups passed. Replacing that source with explicit `SpecialFolder.SystemX86` made the complete synthetic capability inventory pass while preserving the alias guard. The production correction and a Windows regression test must be independently reviewed before another retained qualification attempt.

## Observed host

The available PC runs Windows 11 Home 25H2 build 26200.9711 on an 8-core/16-thread Ryzen 7 3700X with about 16 GiB RAM. An active, unlocked user console has Explorer in session 2, one 3440×1440×32 display, en-GB locale, and GMT Standard Time. Windows PowerShell 5.1, `cmd.exe`, Windows Python 3.13, built-in .NET Framework C# compilers, `System.Windows.Forms`, and `System.Drawing` are available. PyWin32/UI-automation packages and dedicated debugger/capture utilities were not found. Standard Windows token, registry, Job, User32, GDI, and session APIs remain available through C# or Python `ctypes`.

The private clean source remains read-only and separate: 760 files, 483,574,706 bytes, exact clean-manifest SHA-256 `920cbf75653473d276cd33fbbe7a90553dcd6fff4c0878e848aaca7736dddac6`, and official executable SHA-256 `0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86`. Windows independently reproduced the executable identity. The official ISO SHA-256 is `853134bbfc9e774424e62f9694ad7fe9dd7361c8bab93033f82fc906b31a5c53` and was mounted as the expected optical volume during the probe. Private source locations are deployment configuration and are not recorded here.

No CM01/02 process was running after the probe. The executable was not launched and repository/private inputs were not modified.

## Unsafe direct-launch finding

Windows processes started through the reachable WSL interop channel run with a high-integrity administrator token and `SeDebugPrivilege`. The 32-bit Sports Interactive registry key points at the user's modified Program Files installation. Static inspection shows the original startup requests `KEY_ALL_ACCESS`; an elevated direct launch could open that key and change its working directory into the modified installation.

Therefore the original executable must not be launched directly from WSL. This is a reference-integrity and user-installation safety requirement, not merely an automation preference.

The key grants ordinary Users read access rather than full control. A medium-integrity launch should receive `ACCESS_DENIED` for that exact all-access request and retain the supplied working directory, but the launcher must prove this with the exact token before every game start.

## Provisional launcher design

The smallest safe adapter uses built-in Windows APIs and must:

1. duplicate the active Explorer process's medium-integrity primary token and verify user SID, session, elevation, integrity level, active console, and unlocked input desktop;
2. run an exact-token registry preflight and abort unless `RegOpenKeyEx(KEY_ALL_ACCESS)` returns `ACCESS_DENIED`;
3. create a new bounded NTFS attempt directory outside Program Files and the installed-game path, copy the 760-file clean tree, then verify the clean manifest and absence of extras;
4. retain pre-run manifests for the installed folder and matching per-user VirtualStore location;
5. create the game suspended with a sanitized environment and the attempt directory as its explicit current directory;
6. assign it before resume to a Windows Job with kill-on-close, active-process and memory limits, plus an external monotonic timeout;
7. use only the bounded launch flags `-windowed -nosound -nonetwork -ignoreenv -seed 1`; this seed does not make all wall-clock reads deterministic;
8. drive foreground-verified `SendInput`, retain the client-relative input stream, and capture raw client BMPs with desktop `BitBlt`; `PostMessage` and `PrintWindow` are diagnostic only;
9. close gracefully, then terminate the Job after a bounded grace period; and
10. retain token/window/process/module metadata, input events, screenshot identities, created/changed files, and installed-folder/VirtualStore post-run manifests while keeping execution status separate from comparison verdict.

Registry-preflight failure, locked desktop, blank capture, installed-folder or VirtualStore mutation, timeout, or unexplained output is failed/inconclusive evidence, never a pass.

## Before the original executable

The token/job/input/capture helper must first pass independent review and synthetic Windows Forms fixture tests for medium-token/session identity, exact registry denial, isolated current directory, sanitized environment, deterministic input/screenshot capture, timeout/process-tree cleanup, locked-desktop refusal, attempt/path reuse rejection, and absence of installed/VirtualStore mutation.

Only then may a bounded original startup A/A observation use two fresh clean copies with identical display state, flags, seed, and input stream. The first comparison retains unmasked exact endpoint BMPs and generated files. Any difference remains evidence to classify—clock, animation, input timing, layout, or another cause—and cannot be hidden by a tolerance. The ten-repeat P02 corpus remains a later gate.
