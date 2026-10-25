# PC-R9b bounded file-use provenance repair (experimental)

Status: one reviewed four-arm campaign completed and failed its observer-policy gate. File-use provenance remains unknown. The frozen design below belongs to exact experimental source 1007f45; its executed archive and all failures are retained privately. Prior R9 failures are immutable.

The claim is affirmative Linux Bosman host-API file observation, never an original
Windows process result or a whole-kernel-I/O census. Successful open, positive
read delivery and mmap establishment are separate. mmap does not establish page
access. API counts overlap and can nest; byte totals are not unique bytes consumed.
`fread` reports complete delivered items and `items * size` as a lower bound:
a trailing partial item can have delivered additional bytes not represented by its
return. Errors do not erase positive delivery. No semantic-use claim follows.

Descriptor lifetime is a separate qualification gate. Post-call fstat is not an
atomic syscall identity. The new candidate policy makes the active interval
single-threaded: after the unchanged original stack re-exec, install an x86-64
seccomp TSYNC policy which kills on clone/clone3/fork/vfork and rejects x32/foreign
syscall architectures. Then require `/proc/self/task` to contain exactly one task.
A clone denial kills the observed process and leaves an incomplete footer, hence
fails completeness and noninterference. No denied clone is allowed to continue
with altered return behavior. Mask all maskable signals across each
observed API plus descriptor inspection; preserve and restore the original mask.
Blocked synchronous faults terminate without a footer. Cookie-stream callbacks, external ptrace/shared descriptor injection and arbitrary hostile code remain outside this
narrow pinned-route claim. Any inability to establish the policy fails activation.
The policy changes observer runtime behavior and must pass exact comparison to
uninstrumented baseline, disabled and A/A endpoints/captured ranges.

Source audit currently finds no explicit pthread/clone/fork invocation in pinned
Bosman src. SDL video/events and optional audio initialize external libraries;
those may create threads. The sandbox is deliberately fail-closed if that occurs.
Runtime admission cannot rely only on source grep or unchanged pre/post identity.

Bounded design before execution: aggregate by actual resolved fd identity plus API;
retain exact operation/success/failure/errno/positive-result/complete-item counters,
requested-byte totals and API returned-byte lower bounds, all checked uint64.
Retain bounded abnormal details privately, including all failed calls, unresolved
identities, path escapes/symlink observations and drift. Identity/path/aggregate/
abnormal/output caps freeze before source review; saturation/overflow/lost records,
write failure, incomplete footer or unresolved required identity fails completeness.
Neither limits nor definitions may be changed after an arm starts.

Reuse exact R5 baseline/derivative/source/smoke/clean manifest. New exclusive private
build and campaign attempt directories only; never overwrite/reopen old artifacts.
Initially one independently reviewed four-arm serial campaign: baseline, derivative
with file observer absent, enabled A, enabled B. Unchanged R5 sparse capture in all
derivative arms. Seed 1, fixed clock, classic settings, exact R5 14-day actions.
Each arm: wall 240s, CPU 300s, address space 6 GiB, file 64 MiB, stdout/stderr
1 MiB each. Observer stream cap 16 MiB. Compare each save to all arms and retained
R5 exactly, each complete derivative sparse capture to all derivatives and retained
R5 exactly; no masks/tolerances. Revalidate source/tools/build/input before/after
every arm. Freeze compiler/commands/source/input seals before execution; hash and
execute the executable through the same held descriptor. All failed arms remain.
Execution, completeness, endpoint equality, captured-range equality and original/
Bosman comparison are separate verdicts. Original/Bosman comparison stays not-run.

Controls required: descriptor reuse and actual identity, concurrent close/reuse
attempt killed rather than falsely admitted, nested API accounting, positive/error
and partial fread semantics, open-only vs read vs map-only, missing/truncated/footer
count/counter overflow/table/abnormal/output saturation, wrong identities, stack
reexec exclusive activation, signal-mask restoration, endpoint/capture mismatches.
Independent reviewer B and lead review exact committed source before heavy slot.
No qualified result exists at this design revision.
Frozen format `PCR9BFILE1`: one mandatory policy line, up to 2,048 aggregate
rows, up to 1,024 individual abnormal-event rows, and `PCR9BDONE` with exact
operation/row/abnormal/error counts. Each path buffer is 1,024 bytes (a resolved
path reaching the terminating bound fails identity); uint64 overflow sets the
failure bit. Worst-case bounded output remains below the independent 16 MiB cap;
write/truncation/saturation failure leaves errors or missing footer and rejects.
Aggregate keys include API, resolved dev/inode/size/path, status/sample errno and
supplied open path; counts preserve all attempts, positive results, requested/API
delivered-byte lower bounds, complete fread items, nested calls and short
multi-byte fread calls. Only sampled error errno is claimed for stdio stream
errors; it may be stale and is not asserted as their cause. Any positive delivery
with missing/mismatched identity fails even when the stream also reports error.
Abnormal details retain sequence, row identity, fd, request/delivery and sampled
errno for every failed call and successful outside-root/unresolved operation.
Supplied open paths and their exact counts also survive in aggregate rows;
absolute symlink observations at analysis time are labeled as such. Relative
symlink paths are unresolved rather than reconstructed using later cwd state.
Clean manifest validation forbids clean-path symlinks and checks all members.

Source/tool freeze includes all four new Python/C source/control files, this
contract, exact compiler executable/version/command, built library, Python, libc,
loader and the ldd-reported transitive DT_NEEDED dependency set of the R5 derivative. This does not census modules loaded later through dlopen. All listed files are sealed
before/after each arm together with source/tree, smoke, R5 receipt/observer and
clean inputs. The official source boundary is unchanged; the new seccomp policy
is a separate observer runtime intervention explicitly evaluated for endpoint
and captured-range noninterference only. One review author cannot admit their
own result. Model: assigned GPT-6.1 Sol/medium; B reviews source, A/lead artifacts.

Small controls have passed at working-source level. They compile only tiny
synthetic programs/observer variants in fresh retained private directories and
never launch the game. These are mechanism tests, not provenance qualification.
The native production observer build and four-arm campaign remain pending exact
independent review and lead allocation of the single heavy slot.
Pre-execution review found and corrected an observer entry race: nesting depth
must not become visible before signals are blocked. Each API now first uses raw
x86-64 `rt_sigprocmask` with an eight-byte full kernel mask (including NPTL's two
reserved signals), then publishes depth; only the outer entry saves/restores the
prior mask. A pending SIGUSR1 control actually dup2-reuses the read descriptor:
the first read binds its original identity before deferred handler delivery, and
the next pread binds the replacement. Separate nested-API and preexisting-thread
controls exercise exact counts and TSYNC/census rejection. Eleven controls pass;
one initial signal-control helper compile failure is retained privately, corrected
without weakening `-Werror` or any acceptance threshold.
## Executed bounded result: retained observer-policy failure

Independent B review approved exact [1007f45fc5f6267ee283ffc804754d39cf8c9f9a](https://github.com/derekrivers/CM0102_Simulation_Lab/commit/1007f45fc5f6267ee283ffc804754d39cf8c9f9a)
after independently repeating eleven mechanism controls. Lead then allocated the
single heavy slot for one observer build and one frozen four-arm campaign. The
26,232-byte library has SHA-256
`667cf38d6b99f05018025b79ed249e84e3ed21c7f0e0d293722d334811c757f4`.
The compiler was Ubuntu cc 13.3.0; compile/seal elapsed 0.465 seconds. Frozen
sources, exact commands/environment, compiler/build receipts and all outputs
remain in fresh private directories. No original Windows process was launched.

The [sanitized failed receipt](evidence/pc-r9b-attempt1-failed-policy-v1.json)
records 368.100230688 seconds between the campaign's contemporaneous seals:

| Arm | Actual seconds | Execution | Observation |
| --- | ---: | --- | --- |
| Baseline | 83.136259 | reached 14-day endpoint | disabled |
| R5 derivative, file observer absent | 83.290129 | reached 14-day endpoint | disabled |
| Observed A | 99.873491 | SIGSYS, exit -31 | incomplete |
| Observed B | 91.602489 | SIGSYS, exit -31 | incomplete |

Two of four executions succeeded; zero of two observations are complete. Both
observed processes failed under the explicit single-task policy. SIGSYS alone
does not identify the forbidden syscall or library route, so no specific SDL,
clone or fork cause is asserted. Neither observed arm produced its endpoint save
or R5 sparse capture. Each retained trace is exactly 55 bytes, SHA-256
`3ac738bbbcbb6da661af58288b1d7c3f29141747d61eb02f159ae2f0b450da21`,
containing the header and policy line only. There is no aggregate table or footer.
Because aggregation flushes at the destructor, operation/byte/error counters and
file observations are **unknown**, never zero. Missing footer correctly rejects
completeness. No limit or policy changed and no repeat campaign was run.

The two actual successful saves exactly equal each other and retained R5:
18,975,625 bytes, SHA-256
`8e3a60abb32ae8864e32052de34aa2fea00f1709ef54531220e949eb0ba16f11`.
The disabled derivative's complete 3,849,184-byte capture exactly equals retained
R5, SHA-256
`014808018f7b20f60abaac5c71a0c509747259e309563650afe0d0cc79da6f40`.
These are successful-subset comparisons only. Four-arm endpoint and captured-range
noninterference fail because the observed outputs are absent. Full live-state,
clean-file consumption, mapped-page access and original-process parity remain
unqualified; original/Bosman comparison remains not-run.

Source, observer/build/tool identities, the ldd-reported 49 dependencies and all
760 clean manifest members remained stable through every before/after arm seal.
Independent A artifact review rehashed all 155 private artifact seals, actual
manifest members and descriptor identities, five executed source files and all
eight chronological arm seals. It independently parsed the two actual traces
without importing the producer parser and compared complete save/capture bytes.
Final report-head review and its sanitized audit receipt are separate gates.

The precise blocker is incompatibility of this single-task observation policy
with an unidentified forbidden syscall on the frozen platform route. Bounded
aggregation mechanisms pass synthetic controls but have no complete actual
file-use observation. The observer, driver and controls remain on the
[experimental branch](https://github.com/derekrivers/CM0102_Simulation_Lab/tree/codex/pc-r9b);
main may receive only independently reviewed truthful reports and receipts.
Reproduction requires the exact linked experimental source, rather than absent
main-tree scripts. Any diagnosis or new experiment requires its own frozen
source, lifecycle/identity justification, budget and independent review; this
allocation authorizes no follow-up. All prior and current failed paths remain.