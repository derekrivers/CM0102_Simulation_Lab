# P02 preliminary Windows reference-host probe

Date: 24 October 2026

Status: preliminary read-only observations without an immutable probe artifact; host qualification, launcher implementation, and all original behaviour remain pending.

## Evidence boundary

These observations were collected on 24 October 2026 through bounded WSL and Windows PowerShell/`cmd.exe` inventory commands during the active Codex session. They included OS/session/process inventory, token privilege and integrity queries, registry value/ACL/access probes, tool discovery, filesystem mode/type/count/hash checks, independent Windows executable hashing, mounted-volume inspection, and process absence checks. No versioned probe script, canonical command transcript, sanitized output bundle, or artifact hashes were retained.

The exact host, token, privilege, registry, and tooling statements below are therefore unverified operational observations that define what the reproducible qualification probe must test; they are not yet durable gate evidence. Before any original launch, rerun them through a reviewed versioned probe and retain its canonical request, sanitized outputs, tool revision, completeness flags, and hashes. Any discrepancy invalidates the provisional launcher assumptions.

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
