# Local execution request v1

The B1 local process contract is implemented by `lab-cli`. It validates a bounded JSON request before creating an attempt or starting a process, then runs a protocol-speaking backend with a cleared, allowlisted environment. `lab-bosman-adapter` supplies the first deliberately narrow Bosman-native endpoint: a clean, classic-mode, fixed-clock and seeded two-run save-equality check.

## Commands

```sh
cargo run -p lab-cli -- validate-run --request request.json

cargo run -p lab-cli -- execute-process \
  --request request.json \
  --backend-executable /private/path/to/protocol-backend \
  --backend-config /private/path/to/bosman-paths.json \
  --attempt-dir /private/path/to/new-attempt
```

`validate-run` emits a stable SHA-256 over the parsed, canonical request. `execute-process` opens and hashes the executable once, then executes that same open file to avoid a pathname-replacement race. It verifies the hash before attempt creation, refuses an existing attempt directory, uses private `HOME` and temporary directories, clears inherited environment variables, and places the backend in its own process group. The Linux supervisor is also a child subreaper, so descendants that escape the process group are adopted and killed. Pipe I/O is cancellable and timeout or output-limit failure cannot wait indefinitely on an inherited descriptor. The private config is required for `bosman-native`, rejected for `synthetic-test`, and used only as a deployment locator; its private paths are not copied into the request or replay manifest.

## Request bounds

The top-level request and every nested object reject unknown fields. Version 1 requires:

- safe attempt, scenario, profile, command, and stop-condition identifiers;
- backend kind `bosman-native` or `synthetic-test`, a 40-character source revision, and the expected executable SHA-256;
- a timeout from 1 ms through 3,600,000 ms;
- independent stdout and stderr limits from 1 MiB through 16 MiB;
- at most 256 input identities and 256 uniquely identified commands; and
- exactly four input identities for the currently accepted `bosman-native` profile.

The complete request file is limited to 1 MiB. Input identities contain only byte count and SHA-256; private paths and proprietary bytes do not enter the request or replay manifest.

The only accepted Bosman command in version 1 is `bosman-classic-same-save-v1`. Its parameters are fixed to classic mode, 14 game days, two concurrent `normal,again` runs, seed 1, fixed clock, and byte-identical saves. Its four positional input slots bind the native Bosman executable, clean-file manifest, pinned smoke runner, and Python interpreter. The expected stop condition is `classic-same-save-normal-again-14-days-equal`. This intentionally prevents the general command envelope from silently selecting another runner mode or weaker endpoint.

The private backend config is strict JSON with absolute deployment paths named `python_executable`, `smoke_runner`, `bosman_executable`, `clean_game_dir`, and `clean_manifest`. The adapter verifies the four declared file identities, validates every clean-tree manifest row and rejects traversal, symlinks, missing/extra files, writable source entries, size drift, hash drift, duplicate paths, and case collisions. It invokes the Bosman executable through the adapter's restricted launcher, which accepts only `--game <configured-clean-dir> -seed 1`, rehashes the executable, executes the same open file descriptor, and forwards only the required runtime environment variables.

## Child protocol

The validated canonical request is sent on standard input. Standard output is NDJSON protocol only and standard error is diagnostic output. Each line is limited to 64 KiB and must contain protocol version 1, the request attempt ID, a contiguous zero-based sequence, a message kind, and an object payload.

The first frame must be exactly one handshake. Its backend kind, source revision, and executable hash must match the request, and its capability identifiers must be safe and unique. Exactly one terminal frame must be last. Version 1 accepts success only when the process exits zero and the terminal reports `succeeded`, `completed-target`, and the declared stop condition. Process success does not imply comparison equality.

On success the new attempt directory contains atomically published `request.json`, `stdout.ndjson`, `stderr.log`, and `replay-manifest.json`. The retained request is canonical, does not add the supervisor's request, executable, or attempt paths, and makes the attempt self-contained for replay. The manifest binds it, the command stream, inputs, backend identity, limits, terminal outcome, and captured artifacts by digest. Its comparison verdict remains `not-run`.

## Deliberate limits

The process layer has a synthetic protocol fixture and negative controls for malformed requests, identity mismatch, inherited-secret removal, ordering, terminal endpoint, output cap, timeout/process-tree cleanup, and attempt reuse. The Bosman endpoint additionally requires exact runner output for both 14-day saves, a positive normal-run idle-sleep count, the byte-equality assertion, and final `PASS` before it emits success.

The adapter is intentionally not a general Bosman automation API. Failed attempts are not yet atomically retained as structured evidence, nested trusted-runner capture is checked after process completion rather than streamed through an independent cap, and the supervisor does not yet enforce cgroup CPU/RAM limits or leases. Original-executable observation and original-versus-Bosman comparison remain separate work; a successful Bosman replay manifest keeps `comparison_verdict: not-run`.
