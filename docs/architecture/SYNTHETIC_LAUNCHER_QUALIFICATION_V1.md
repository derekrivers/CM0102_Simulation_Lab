# Synthetic Windows launcher qualification v1

Status: the host-stability prerequisite is accepted at merge `b9123ffc7f8261f0b87c354eeb3a77d728540825`. This contract freezes the next synthetic-only sequence. The harmless fixture and its retained no-UI build record form the first candidate implementation increment; clean exact-revision review and merge remain pending. The controller, live-UI retained harness, private UI qualification evidence, and every original-process observation remain pending.

## Purpose and authority boundary

This gate tests the Windows mechanisms needed to construct a safe original-observation adapter without launching or accepting the original executable. It uses a repository-owned, asset-free Windows Forms fixture. Passing the gate may authorize work on a separately reviewed original-launch contract; it cannot authorize an original launch or establish original behaviour, parity, game fidelity, or P02 closure.

The existing original-host probe and its verifier, harness, retained attempts, and comparator are frozen inputs. Launcher code must live in a separate directory and must not be imported into or compiled with that read-only probe. The synthetic stack accepts no game executable, game directory, clean data, ISO, patch, save, arbitrary child command, shell command, or free-form argument list.

The accepted private host artifact is exactly 3,310 bytes with SHA-256 `96e38bb7932e1acb64aa7c9a33012f3425318b3a8e3aaf7ce98aaf8e1cd27659`. It records `original_execution_status: not-run` and `original_behavior_qualified: false`; the synthetic stack must preserve both facts.

## Staged delivery

1. Freeze this contract and the public profile, add the harmless fixture and pure/static tests, and compile/test it on Windows. This increment contains no process-creation authority.
2. Add the synthetic-only controller, strict verifier, retained-run harness, and fault seams. Independently review the exact revision before any live UI launch.
3. Run the reviewed build on the qualified PC: two fresh UI attempts from byte-identical build copies, two timeout/tree-cleanup attempts, the locked-desktop refusal, and the negative matrix. Independently review the retained evidence before accepting this gate.
4. Specify a separate original-launch contract, including clean-tree copy/verification and original-specific retention. Review and test those additions with synthetic inputs before any original launch.

No stage may be collapsed by relabelling compile success, a process exit, or Bosman evidence as Windows fixture qualification.

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

Test-only failure simulation belongs in the controller test assembly or a separately compiled test fixture. It must not add hidden modes, process creation, or other authority to the production fixture image.

## Synthetic-only controller boundary

The later controller is an x86 .NET Framework console image with one fixed sibling target name, `SyntheticLauncherFixture.exe`. It accepts no executable path/name/hash argument and contains no shell, `Process.Start`, `ShellExecute`, `cmd.exe`, PowerShell, PATH search, or alternative process-creation API. The private fixed-name configuration contains expected identities and protected guard paths but no executable path.

The exact process-creation API selected for version 1 is `CreateProcessAsUserW`. The accepted host report proves only that the high-integrity caller has enabled `SeImpersonatePrivilege`, contains `SeIncreaseQuotaPrivilege` so it can be explicitly enabled, and uses the same account/session as the limited Explorer token. `SeAssignPrimaryTokenPrivilege` was not observed. Those facts do **not** prove that the Explorer token is a restricted or linked derivative of the caller token, so they do not establish the documented restricted-token assignment exemption. Version 1 treats `CreateProcessAsUserW` as an unproven synthetic-only capability hypothesis: the controller must explicitly enable `SeIncreaseQuotaPrivilege` and either separately prove the required token relationship or fail closed. Error `1314`, a missing relationship proof, or any other creation failure is a failed capability result. There is no `CreateProcessWithTokenW` fallback and no retry through a different API.

The controller must bind its own and the fixed fixture's bytes, final paths, file IDs, link counts, reparse status, source/config identities, and before/after identities. It must reject aliases, hardlinks, reparse points, mutation, overlap, existing attempt output, non-private parents, and alternate mount views. Build and runtime copies are ordinary copies, never hardlinks.

## Required live sequence

For a normal UI attempt the reviewed controller must, in order:

1. bind the accepted host artifact, exact build inputs, fixed target and fresh private attempt root;
2. require zero CM01/02 processes and a stable active `Default` input desktop;
3. resolve the shell through `GetShellWindow`, require its final image to be the in-box Explorer in the active console session, and open that exact process token;
4. duplicate one least-rights primary token and verify same user, session, medium integrity, limited elevation, non-administrator state, and expected privilege tuple;
5. impersonate from the same source token for the exact 32-bit `RegOpenKeyExA` all-access request and require only Win32 `5` (`ERROR_ACCESS_DENIED`), then revert and prove controller-token restoration;
6. capture registry last-write and complete installed-tree and matching VirtualStore summaries;
7. construct a sorted double-NUL Unicode environment block from the exact allowlist without inheriting the controller environment;
8. create the fixed fixture suspended on `winsta0\\default`, with the explicit attempt working directory and `bInheritHandles=false`;
9. configure an unnamed non-inheritable Job with kill-on-close, no breakaway, active-process and process/job-memory limits; assign and verify membership before the only resume;
10. prove the unique visible unowned top-level window belongs to the exact child and matches the protocol, state, client geometry, session, desktop, display, and DPI assumptions;
11. require all relevant input up and the exact child window foreground immediately before input; requesting focus may be attempted, but refusal is not bypassed;
12. use `SendInput` for the frozen client-relative click with the nonce in `dwExtraInfo`, require the exact event count, and independently prove the state transition;
13. capture the mapped client rectangle twice before and twice after from the desktop DC with `BitBlt`, emit a hand-written canonical 24-bit BMP privately, and require every byte to match the generated pixel plan and repeat;
14. request orderly close, apply the bounded grace interval, close or terminate the Job when required, wait known handles, and prove the Job is empty; and
15. rebind all inputs and guards, require stable registry/installed/VirtualStore observations and zero CM01/02 processes, then publish one canonical privacy-scanned report without replacement.

No `AttachThreadInput`, `PostMessage` input, `PrintWindow`, screenshot tolerance, alternate capture route, window-title data channel, inherited environment, handle inheritance, or best-effort registry result can qualify.

## Required scenarios and negative controls

Qualification requires these separately named retained scenarios from the same exact reviewed build/profile:

- `ui-success-v1`: two fresh attempts with exact semantic agreement and byte-identical ready/complete BMPs across attempts;
- `tree-timeout-v1`: two attempts in which a test-only fixed fixture creates one fixed descendant, the bounded timeout terminates the whole Job, and active process count becomes zero; and
- `locked-refusal-v1`: a real locked/non-Default desktop is detected by a preflight-only route that has no process-creation capability, with zero fixture processes and artifacts.

Public fault tests must also cover token/SID/session/integrity/elevation drift; registry results other than exactly 5; impersonation restoration failure; privilege/API fallback attempts; environment extras/case collisions/secret inheritance; resume-before-assignment; Job assignment/membership/limit/cleanup failures; partial or zero `SendInput`; wrong nonce/button/coordinate/state/window/PID; focus theft; locked/secure desktop; display/DPI/geometry drift; blank, occluded, unstable, one-pixel-different, malformed, or neighboring capture; graceful-close failure; fixture/config/source/compiler replacement; reparse/hardlink/alias/overlap; existing output; timeout/output caps; installed/VirtualStore/registry mutation; and a game process before or after.

Unexpected pixels are compared in memory, then discarded and zeroed rather than retained, because a capture-boundary defect could include private neighboring content. Only exact approved synthetic BMPs may be retained.

## Evidence and privacy

The strict public report separates fixture execution from comparison and original status. A successful summary is exactly equivalent to:

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

Reports and manifests must never contain raw paths, usernames, hostnames, SIDs, environment values, registry Location text, window titles, exception type/message/stack, command lines, HWND/PID values, or unexpected screen bytes. They bind private inputs by byte count and SHA-256 and use fixed argument roles. Retained evidence binds source revision and bytes, compiler and companion, absolute framework references, public/private configuration, controller and fixture before/after, exit/stream/time limits, scenario artifacts, verifier identity, and no-replace publication.

The same-account active-interference and compromised-kernel exclusions from the accepted host contract remain. A display/session switch, RDP transition, UAC secure desktop, or concurrent user input invalidates an attempt.

## Acceptance and carry-forward

The fixture increment passes only when its C# policy tests, Python static/profile tests, exact x86 Windows build, and Windows no-UI test executable pass at one reviewed revision. It does not qualify the launcher.

The complete synthetic gate passes only after the controller/harness revision and private scenario evidence are independently reviewed and merged. Even then, clean-tree copying, exact original-image binding, original flags, original-specific output retention, and the first bounded original startup remain separate reviewed gates. The game remains never launched until all of those gates are satisfied and explicitly recorded.
