# PC-R9 bounded Bosman file-use provenance

## Frozen claim and observation boundary

This experiment reuses R5's exact sealed baseline and capture derivative on pinned
Bosman 144ed82c248228c7769c6785899527eae5b33c3d. It observes host file API results
with a separately compiled LD_PRELOAD library; it does not modify the game source,
existing build, R5 observer or old artifacts. The instrumented process is Linux
Bosman, never the original Windows executable.

The observer wraps open/open64/openat/openat64, fopen/fopen64, read/pread/pread64,
fread/fread_unlocked and mmap/mmap64. Operations inspect the live descriptor immediately after the API returns and
record its resolved /proc/self/fd target and fstat device/inode/size, requested count,
returned count, operation, sequence and errno for failures. Requested open paths
and failed operations are retained privately. No file content is logged.
Positive read counts (including counts accompanied by a stream error) prove
complete items delivered through that API; a successful open
alone does not. mmap success proves a mapping was established, not that its pages
were read. No claim covers semantic use of every byte or unwrapped/direct-system-
call/internal-libc I/O. Observations are affirmative evidence within this stated
interposition boundary during the constructor-to-destructor observer-active
interval, not a census of all kernel file activity. Loader I/O before/after that
interval is outside scope. Descriptor inspection is not atomic with a concurrent
close/reuse from another thread: that wider lifetime race is unqualified. The
pinned host/posix.c supplies the host_fopen-to-fopen route; its identity is sealed. No
claim of general concurrent descriptor-lifetime safety follows.

An original clean manifest member is bound only when resolved path, device/inode,
size and SHA-256 identity agree with the contemporaneously sealed clean inventory.
All other successes, failures, symlink observations at analysis time, escapes and identity mismatches stay
in the private trace/summary. Public evidence publishes only aggregate structural
counts and artifact hashes. It never publishes raw paths, names, proprietary bytes
or traces. Missing/invalid footer, dropped/truncated records or observer failure
makes observation completeness fail; successful game execution cannot override it.

## Noninterference and bounded experiment acceptance

Before execution, independently review exact observer/driver/contract revision.
Compile only the new library into a fresh private output; seal source, compiler,
command and resulting library. Revalidate R5 build receipt, baseline, derivative,
pinned source/tree, pinned smoke script and all 760 clean files before each arm
and after each arm. Hash and execute each binary through the same held descriptor.
No source, deployment, CI, pin or original launcher changes are authorized here.

Run four serial 14-day fixed-clock seed-1 arms with classic settings and the exact
R5 smoke actions: retained baseline, R5 derivative with file observer absent,
derivative + file observer A, derivative + file observer B. Enable the unchanged
R5 sparse capture in all derivative arms. Each arm has a fresh private HOME/user
directory, 240-second wall deadline, CPU 300 seconds, 6 GiB address-space limit,
64 MiB per file and 1 MiB each stdout/stderr cap. Trace cap is 16 MiB; overflow
must visibly invalidate observation rather than silently omit evidence.
All attempts and failed arms are retained, with exclusive new output directories.

Compare exact endpoint saves across all four arms and the retained R5 endpoint,
and complete raw sparse captures across the three derivative arms and retained
R5 capture. No masks or tolerances. These comparisons support only the observed
endpoint and captured live ranges; endpoint equality is never full live-state
equality. Timing differences are reported, not hidden. The observer changes host
I/O and scheduling, which remains a wider noninterference limitation.

Receipts separate execution_status, observation_completeness,
endpoint_noninterference, captured_ranges_noninterference and comparison_verdict
(not-run for original/Bosman comparison). They retain hashes/times/configuration,
tool/build/input seals, failed/denied/escape/symlink counts and private raw traces.
Reproducible controls must catch missing/truncated/dropped traces, wrong identities,
positive-read versus open-only versus mmap-only confusion, and endpoint mismatch.
Independent artifact/seal/result verification and exact final-head review are
required before evidence promotion or merge. A failed experiment is retained with
a precise blocker; hashes alone never upgrade consumption unknown to passed.

## Routing and budget

Lead owns observer/driver and experiment. GPT-6 Astra/high owns R7; GPT-6.1
Sol/medium owns R8. A separate worker reviews this frozen experiment before
execution and the artifacts afterward. No nested agents; one heavy job at a time.
At most one four-arm campaign is initially admitted; a failure requires diagnosis
and a separately retained bounded follow-up. Token/billing totals are unavailable.

## Retained first failure and reviewed follow-up

The first four-arm campaign at exact source 5cb1e0b is retained privately as
pc-r9-file-use-5cb1e0b-a1. Baseline and disabled reached their endpoints in
83.29 and 83.07 seconds. Both observed arms exited 124 after about 0.02 seconds,
with incomplete two-operation traces and no endpoint/capture. Their observation
completeness and noninterference verdicts failed; no file-use result is promoted.

Pinned host/posix.c raise_stack runs as an original startup constructor. It raises
the stack limit, sets RECOMP_STACK_SET=1, opens/reads its command line and re-execs
/proc/self/exe. The observer's first constructor created its exclusive trace;
the legitimate second image could not create it again. Independent source and
retained trace review confirmed that exact boundary. The failure is an observer
lifecycle defect, not an original/Bosman parity result.

One separately retained four-arm follow-up is authorized after exact-source
independent review. Only observed arms explicitly set PC_R9_WAIT_FOR_STACK_REEXEC.
When that flag is present and original RECOMP_STACK_SET is absent, the observer
defers activation and creates no trace. The unchanged original stack re-exec
then activates the observer in its second image. Missing expected re-exec yields
missing trace and a failed completeness verdict. No first trace is deleted,
reopened or appended; no original source, stack limits or RECOMP_STACK_SET value
is modified by the observer/driver. The observation interval is explicitly the
post-stack-reexec constructor-to-destructor interval. Pre-reexec I/O remains
outside scope. A synthetic control reproduces ungated exit124 then verifies the
gated re-exec's exclusive complete trace and actual positive read evidence.
