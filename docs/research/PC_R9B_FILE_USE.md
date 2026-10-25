# PC-R9b bounded file-use provenance repair (experimental)

Status: design freeze candidate; no native observer build or game campaign authorized
or executed at this revision. This file and all `pc_r9b*` code stay experimental
until independent exact-source/evidence review. Prior R9 failures are immutable.

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