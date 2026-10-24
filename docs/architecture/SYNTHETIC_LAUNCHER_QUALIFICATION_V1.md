# Synthetic Windows launcher qualification v1

Status: the host-stability prerequisite is accepted at merge `b9123ffc7f8261f0b87c354eeb3a77d728540825`. The harmless fixture and retained no-UI build record are accepted at merge `4a8a2f5e65006ec6a4df8d980949af849e098a43`; the authority-free controller policy scaffold is accepted at merge `cbb54d081754eadcc4ce8657212b6517fb863e7a`. The live controller, process/native adapter, retained live-UI harness, private UI qualification evidence, and every original-process observation remain pending.

## Purpose and authority boundary

This gate tests the Windows mechanisms needed to construct a safe original-observation adapter without launching or accepting the original executable. It uses a repository-owned, asset-free Windows Forms fixture. Passing the gate may authorize work on a separately reviewed original-launch contract; it cannot authorize an original launch or establish original behaviour, parity, game fidelity, or P02 closure.

The existing original-host probe and its verifier, harness, retained attempts, and comparator are frozen inputs. Launcher code must live in a separate directory and must not be imported into or compiled with that read-only probe. The synthetic stack accepts no game executable, game directory, clean data, ISO, patch, save, arbitrary child command, shell command, or free-form argument list.

The accepted private host artifact is exactly 3,310 bytes with SHA-256 `96e38bb7932e1acb64aa7c9a33012f3425318b3a8e3aaf7ce98aaf8e1cd27659`. It records `original_execution_status: not-run` and `original_behavior_qualified: false`; the synthetic stack must preserve both facts.

## Staged delivery

1. Freeze this contract and the public profile, add the harmless fixture and pure/static tests, and compile/test it on Windows. This increment contains no process-creation authority.
2. Add the synthetic-only controller, fixed-target outer supervisor, dedicated timeout root/child fixtures, separately built locked-refusal preflight image, strict verifier, retained-run harness, and fault seams. The public profile for this implementation revision must say `build-unpinned`; its run mode must reject that state before calling any process-creation API. A retained build may compile the production images, inspect them statically, and execute only the pure console test assemblies. It must record every controller/supervisor/fixture/preflight image as not executed, every fixture execution as `not-run`, and qualification as false. Independently review that exact source and retained no-UI build before changing the profile.
3. In a separate control-only revision, pin the exact byte count and SHA-256 of every live image and all reviewed build inputs, update the exact-const profile schema and verifier to accept only that pinned state, and replace the build-unpinned report grammar with scenario-specific eligible implications. Repeat the static, build, no-UI and negative controls and independently review the exact revision. No production C# source changes are allowed in that transition. Only that accepted revision may make the live-run route reachable.
4. Run the reviewed pinned build on the qualified PC: two fresh UI attempts from byte-identical build copies, two timeout/tree-cleanup attempts, the locked-desktop refusal, and the negative matrix. Independently review the retained evidence before accepting this gate.
5. Specify a separate original-launch contract, including clean-tree copy/verification and original-specific retention. Review and test those additions with synthetic inputs before any original launch.

No stage may be collapsed by relabelling compile success, a process exit, or Bosman evidence as Windows fixture qualification. Neither the build-unpinned revision nor its retained build may execute the supervisor, controller, UI fixture, timeout fixtures, or locked-refusal preflight image; compiling an image does not authorize running it.

## Harmless fixture contract

`SyntheticLauncherFixture.exe` is a separate x86 .NET Framework Windows Forms image. It has no controller code or alternate role and accepts no command-line arguments. It may use only the exact environment supplied by the future controller:

- `CM0102_SYNTHETIC_CWD_SHA256`
- `CM0102_SYNTHETIC_INPUT_NONCE`
- `SystemRoot`
- `TEMP`
- `TMP`
- `WINDIR`

The nonce is a nonzero eight-digit lowercase hexadecimal value suitable for the x86 `dwExtraInfo` field. The current-directory hash is lowercase SHA-256 over the exact UTF-16LE current-directory string. `TEMP` and `TMP` must agree, as must `SystemRoot` and `WINDIR`; the future controller additionally proves that the system paths are the expected absolute in-box paths and the temporary path is the fixed child of the attempt root. Unknown, missing, case-colliding, inherited, drive-current-directory, or secret-bearing environment entries fail before a window is created.

Before becoming ready, the fixture independently requires:

- its process session equals the active console session;
- its token has the same policy shape expected from Explorer: medium integrity, limited elevation, not elevated, and not an enabled administrator token; and
- the open input desktop is exactly `Default`.

It creates exactly one visible, unowned top-level form with a fixed title, manual position, `AutoScaleMode.None`, fixed 320 by 240 client area, and no text, font, theme, image, timer, clipboard, network, registry, shell, child process, file access, standard-output, or standard-error dependency. It paints only the profile's exact RGB regions. No raw private value appears in its title or pixels.

The fixed `WM_APP` query messages expose only protocol version and state IDs. The initial state is `ready`. The sole state transition requires a real left-button client click at the frozen target point while `GetMessageExtraInfo()` equals the supplied nonce. Posted-message substitution, the wrong button, coordinate, nonce, state, or a second transition cannot qualify. The `complete` state uses a distinct exact pixel plan and remains visible until orderly close. The fixture never writes an evidence artifact; the controller observes state and captures pixels externally.

Test-only failure simulation belongs in the controller test assembly or a separately compiled test fixture. It must not add hidden modes, process creation, or other authority to the production fixture image. `tree-timeout-v1` uses separately compiled fixed siblings named `SyntheticLauncherTimeoutFixture.exe` and `SyntheticLauncherTimeoutChild.exe`; it never aliases or replaces `SyntheticLauncherFixture.exe`. The public profile binds both timeout-image identities and the exact scenario mapping. The timeout root has one test-only `CreateProcessW` call site whose sole target is the fixed sibling child, with no arguments or path input, and then waits; the child only waits. Neither timeout image contains a selectable role, arbitrary target, shell route, or original-game input.

`locked-refusal-v1` uses a separately compiled fixed sibling named `SyntheticLauncherLockedPreflight.exe`. It accepts no arguments and is not the controller with a mode switch. Its imports and reachable code are limited to binding itself/configuration, checking the active session/input desktop and process absence, and returning the fixed sanitized refusal facts. It must have no process-creation or native-launch import or reachable call (`CreateProcess*`, `CreateProcessAsUser*`, `CreateProcessWithToken*`, `ShellExecute*`, `WinExec`, managed `Process`, or an equivalent), no token duplication, registry access, input, capture, window creation, or fixture target reference. A static verifier and negative mutation tests must establish that absence before the image can be pinned.

## Synthetic-only controller boundary

The later controller is an x86 .NET Framework console image with a closed, public scenario-to-target mapping: `ui-success-v1` maps only to `SyntheticLauncherFixture.exe`, `tree-timeout-v1` maps only to `SyntheticLauncherTimeoutFixture.exe`, and `locked-refusal-v1` is rejected because it is owned by the separate preflight image. It accepts no executable path/name/hash argument and contains no shell, `Process.Start`, `ShellExecute`, `cmd.exe`, PowerShell, PATH search, `CreateProcessW`, or alternative process-creation API. The private fixed-name configuration contains expected identities and protected guard paths but no executable path. All fixed image names, target mappings, and byte identities are public-profile values; a private instance may select one declared scenario but cannot change its target.

The exact process-creation API selected for version 1 is `CreateProcessAsUserW`. The accepted host report proves only that the high-integrity caller has enabled `SeImpersonatePrivilege`, contains `SeIncreaseQuotaPrivilege` so it can be explicitly enabled, and uses the same account/session as the limited Explorer token. `SeAssignPrimaryTokenPrivilege` was not observed. Those facts do **not** prove that the Explorer token is a restricted or linked derivative of the caller token, so they do not establish the documented restricted-token assignment exemption. Version 1 treats `CreateProcessAsUserW` as an unproven synthetic-only capability hypothesis: the controller must explicitly enable `SeIncreaseQuotaPrivilege` and either separately prove the required token relationship or fail closed. Error `1314`, a missing relationship proof, or any other creation failure is a failed capability result. There is no `CreateProcessWithTokenW` fallback and no retry through a different API.

The controller must bind its own and the selected fixed fixture's bytes, final paths, file IDs, link counts, reparse status, source/config identities, and before/after identities. The supervisor additionally binds itself, its selected fixed target, and every image allowed by the scenario; the timeout root binds the fixed timeout child before its sole creation call. They must reject aliases, hardlinks, reparse points, mutation, overlap, existing attempt output, non-private parents, and alternate mount views. Build and runtime copies are ordinary copies, never hardlinks.

`SyntheticLauncherSupervisor.exe` is a harness-only x86 .NET Framework image with no general runner interface. From the fixed private scenario it maps `ui-success-v1` and `tree-timeout-v1` only to `SyntheticLauncherController.exe`, and `locked-refusal-v1` only to `SyntheticLauncherLockedPreflight.exe`. It accepts no command, executable path/name/hash, arguments, or environment override. Its one `CreateProcessW` call site creates only that fixed sibling target suspended with `bInheritHandles=false`. Before the only resume, the supervisor assigns the target to an unnamed, non-inheritable outer Job with kill-on-close, no breakaway, fixed process/memory limits, and an active-process limit covering the exact scenario topology. The outer Job remains held until all known processes and descendants are gone, including after controller failure or timeout.

This outer Job is mandatory containment for the interval between the controller's suspended fixture creation and assignment to the controller's inner Job: because the controller is already in the non-breakaway outer Job, its child enters that Job at creation and cannot escape if the controller crashes before inner assignment. The supervisor's `CreateProcessW` is only the fixed harness-to-controller/preflight launch; it is not a fallback or alternative inside the controller. The production controller's sole process-creation API remains the single fixed-target `CreateProcessAsUserW` call described above. Separately, the timeout root's one test-only `CreateProcessW` call is limited to its fixed timeout child. No other image or route may import or call `CreateProcessW`.

## Required live sequence

For a normal `ui-success-v1` attempt the reviewed controller must, in order:

1. bind the accepted host artifact, exact build inputs, fixed target and fresh private attempt root;
2. require zero CM01/02 processes and a stable active `Default` input desktop;
3. resolve the shell through `GetShellWindow`, require its final image to be the in-box Explorer in the active console session, and open that exact process token;
4. duplicate one least-rights primary token and verify same user, session, medium integrity, limited elevation, non-administrator state, and expected privilege tuple;
5. impersonate from the same source token for the exact 32-bit `RegOpenKeyExA` all-access request and require only Win32 `5` (`ERROR_ACCESS_DENIED`), then revert and prove controller-token restoration;
6. capture registry last-write and complete installed-tree and matching VirtualStore summaries;
7. construct a sorted double-NUL Unicode environment block from the exact allowlist without inheriting the controller environment;
8. create `SyntheticLauncherFixture.exe` suspended on `winsta0\\default`, with the explicit attempt working directory and `bInheritHandles=false`; it is already transitively contained by the supervisor's outer Job;
9. configure an unnamed non-inheritable Job with kill-on-close, no breakaway, active-process and process/job-memory limits; assign and verify membership before the only resume;
10. prove the unique visible unowned top-level window belongs to the exact child and matches the protocol, state, client geometry, session, desktop, display, and DPI assumptions;
11. require all relevant input up and the exact child window foreground immediately before input; requesting focus may be attempted, but refusal is not bypassed;
12. use `SendInput` for the frozen client-relative click with the nonce in `dwExtraInfo`, require the exact event count, and independently prove the state transition;
13. capture the mapped client rectangle twice before and twice after from the desktop DC with `BitBlt`, emit a hand-written canonical 24-bit BMP privately, and require every byte to match the generated pixel plan and repeat;
14. request orderly close, apply the bounded grace interval, close or terminate the Job when required, wait known handles, and prove the Job is empty; and
15. rebind all inputs and guards, require stable registry/installed/VirtualStore observations and zero CM01/02 processes, then publish one canonical privacy-scanned report without replacement.

`tree-timeout-v1` follows steps 1 through 9 with the public mapping selecting `SyntheticLauncherTimeoutFixture.exe`, then requires the fixed timeout root to create its one fixed child, observes the exact two-process inner-Job membership, reaches the bounded timeout without any window/input/capture route, terminates the inner Job, and requires both the inner and supervisor Jobs to become empty before rebinding and publication. `locked-refusal-v1` never enters the controller sequence: the supervisor starts only the separately verified preflight image in its outer Job, and the preflight returns the refusal without opening a process/token handle or creating an attempt/BMP artifact.

No `AttachThreadInput`, `PostMessage` input, `PrintWindow`, screenshot tolerance, alternate capture route, window-title data channel, inherited environment, handle inheritance, or best-effort registry result can qualify.

## Required scenarios and negative controls

Qualification requires these separately named retained scenarios from the same exact reviewed build/profile:

- `ui-success-v1`: two fresh attempts with exact semantic agreement and byte-identical ready/complete BMPs across attempts;
- `tree-timeout-v1`: two attempts in which `SyntheticLauncherTimeoutFixture.exe` creates exactly one `SyntheticLauncherTimeoutChild.exe`, the bounded timeout terminates both inner and outer Jobs, and both active process counts become zero; and
- `locked-refusal-v1`: a real locked/non-Default desktop is detected by `SyntheticLauncherLockedPreflight.exe`, with no process-creation/native-launch capability, zero controller/UI/timeout-fixture processes, and zero BMP or fixture-created artifacts.

For each two-attempt scenario, semantic agreement is computed over the canonical public report by deleting exactly JSON pointers `/bindings/attempt_root_object_id_sha256`, `/bindings/private_configuration/byte_count`, `/bindings/private_configuration/sha256`, `/observations/environment/nonce_sha256`, `/run/attempt_id_sha256`, `/run/attempt_ordinal`, `/run/elapsed_ms`, and `/run/observed_at_utc` and requiring the remaining canonical bytes to be identical. The two private configurations must themselves be canonical and identical after deleting exactly `/guard_paths/attempt_root`; their fresh, non-reused attempt-root values must differ. The canonical retained manifest permits differences only at `/run/observed_at_utc`, `/run/elapsed_ms`, `/inputs/private_configuration/byte_count`, `/inputs/private_configuration/sha256`, `/artifacts/report/byte_count`, and `/artifacts/report/sha256`; the identity differences may arise only from that one private path and the report's eight explicitly removed per-attempt fields. The retained manifest's own external digest may consequently differ. Raw attempt-root paths, file IDs, PIDs, HWNDs, token handles, nonces, SIDs, and other kernel/private values are verified inside each attempt but are omitted; only the listed one-way identities and counters may differ. Controller, supervisor, scenario-mapped image, public configuration, every non-attempt-root private value, source, compiler/reference, verifier, limits, exit, stage/result, guard-summary, and approved-artifact identities must otherwise agree exactly. Ready and complete BMP bytes are identical across `ui-success-v1` attempts, and no timing tolerance, unordered collection, extra ignored path, or value normalization is permitted.

Public fault tests must also cover token/SID/session/integrity/elevation drift; registry results other than exactly 5; impersonation restoration failure; privilege/API fallback attempts; environment extras/case collisions/secret inheritance; resume-before-assignment; inner/outer Job assignment, inheritance, membership, limit, crash-window, and cleanup failures; partial or zero `SendInput`; wrong nonce/button/coordinate/state/window/PID; focus theft; locked/secure desktop; display/DPI/geometry drift; blank, occluded, unstable, one-pixel-different, malformed, or neighboring capture; graceful-close failure; controller/supervisor/UI-fixture/timeout-root/timeout-child/preflight/config/source/compiler replacement or mapping drift; reparse/hardlink/alias/overlap; existing output; non-NTFS storage, inherited/broad/mutated DACLs, alternate streams, or publication replacement; timeout/output caps; installed/VirtualStore/registry mutation; and a game process before or after.

Unexpected pixels are compared in memory, then discarded and zeroed rather than retained, because a capture-boundary defect could include private neighboring content. Only exact approved synthetic BMPs may be retained.

## Evidence and privacy

The strict public report separates fixture execution from comparison and original status. The build-unpinned schema accepts only minimal, ineligible, not-run error reports; it rejects every full, eligible, qualified, or live-observation report. The separately reviewed pinned control revision must add the full-report route plus scenario-specific implications that derive all eligible summary fields from exact checks, observations and empty error lists. Only after that transition, a successful UI summary is exactly equivalent to:

```json
{
  "comparison_verdict": "not-run",
  "fixture_execution_status": "succeeded",
  "original_behavior_qualified": false,
  "original_execution_status": "not-run",
  "qualification_eligible": true,
  "safety_verdict": "synthetic-launcher-qualified"
}
```

Expected timeout cleanup and locked refusal have scenario-specific synthetic verdicts; neither is a successful UI execution. Any contradiction, missing observation, unapproved difference, unsafe guard, malformed artifact, or exception is ineligible/inconclusive.

Reports and manifests must never contain raw paths, usernames, hostnames, SIDs, environment values, registry Location text, window titles, exception type/message/stack, command lines, HWND/PID values, or unexpected screen bytes. They bind private inputs by byte count and SHA-256 and use fixed argument roles. Retained evidence binds source revision and bytes, compiler and companion, absolute framework references, public/private configuration, supervisor, controller, every scenario-mapped fixture/preflight image before and after, exit/stream/time limits, scenario artifacts, verifier identity, and no-replace publication.

Every live attempt root, temporary directory, report staging directory, and retained raw-artifact directory must be a fresh local NTFS directory whose owner is the expected same-account user and whose DACL is protected from inheritance. Its explicit allow ACEs are limited to that exact user SID and `LOCAL SYSTEM`, with no `Everyone`, `Users`, `Authenticated Users`, `Administrators`, service, application-package, network, or unknown SID ACE and no write-through parent or share route. Files are created without a permissive intermediate ACL and inherit only that protected allowlist; the harness reopens and validates the owner, DACL, volume, final path, reparse state, link count, and file identity before execution, before publication, and after cleanup. An unreadable/noncanonical security descriptor, alternate data stream, EFS/compression surprise, inherited/broad ACE, ACL mutation, non-NTFS location, or inability to prove these properties fails closed.

Capture candidates, private configuration, DACL/security-descriptor bytes, guard snapshots, and diagnostic artifacts never leave that protected Windows evidence root and are never committed. Only capture candidates proven byte-identical to the exact approved synthetic BMPs, plus canonical reports/manifests that pass the privacy scanner, may be copied into a separately protected retained publication directory, using create-new/no-replace publication and an immediate identity/DACL recheck. The public report records only fixed booleans and byte-count/SHA-256 bindings for private material; it never serializes account or ACL principals. Unexpected capture bytes are zeroed before any publication attempt.

The same-account active-interference and compromised-kernel exclusions from the accepted host contract remain. A display/session switch, RDP transition, UAC secure desktop, or concurrent user input invalidates an attempt.

## Acceptance and carry-forward

The fixture increment passes only when its C# policy tests, Python static/profile tests, exact x86 Windows build, and Windows no-UI test executable pass at one reviewed revision. It does not qualify the launcher.

The complete synthetic gate passes only after the build-unpinned no-UI revision, the separately pinned live revision, and the private scenario evidence are each independently reviewed and the accepted work is merged. Even then, clean-tree copying, exact original-image binding, original flags, original-specific output retention, and the first bounded original startup remain separate reviewed gates. The synthetic supervisor/controller/preflight accept no original input, and the game remains never launched until all of those gates are satisfied and explicitly recorded.
