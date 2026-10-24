# Local execution request v1

The B1 local process contract is implemented by `lab-cli`. It validates a bounded JSON request before creating an attempt or starting a process, then runs a protocol-speaking backend with a cleared, allowlisted environment. This is transport and evidence infrastructure; the direct Bosman executable does not yet speak this protocol and still needs a dedicated adapter.

## Commands

```sh
cargo run -p lab-cli -- validate-run --request request.json

cargo run -p lab-cli -- execute-process \
  --request request.json \
  --backend-executable /private/path/to/protocol-backend \
  --attempt-dir /private/path/to/new-attempt
```

`validate-run` emits a stable SHA-256 over the parsed, canonical request. `execute-process` opens and hashes the executable once, then executes that same open file to avoid a pathname-replacement race. It verifies the hash before attempt creation, refuses an existing attempt directory, uses private `HOME` and temporary directories, clears inherited environment variables, and places the backend in its own process group. The Linux supervisor is also a child subreaper, so descendants that escape the process group are adopted and killed. Pipe I/O is cancellable and timeout or output-limit failure cannot wait indefinitely on an inherited descriptor.

## Request bounds

The top-level request and every nested object reject unknown fields. Version 1 requires:

- safe attempt, scenario, profile, command, and stop-condition identifiers;
- backend kind `bosman-native` or `synthetic-test`, a 40-character source revision, and the expected executable SHA-256;
- a timeout from 1 ms through 3,600,000 ms;
- independent stdout and stderr limits from 1 MiB through 16 MiB;
- at most 256 input identities and 256 uniquely identified commands; and
- at least one input identity for a `bosman-native` request.

The complete request file is limited to 1 MiB. Input identities contain only byte count and SHA-256; private paths and proprietary bytes do not enter the request or replay manifest.

## Child protocol

The validated canonical request is sent on standard input. Standard output is NDJSON protocol only and standard error is diagnostic output. Each line is limited to 64 KiB and must contain protocol version 1, the request attempt ID, a contiguous zero-based sequence, a message kind, and an object payload.

The first frame must be exactly one handshake. Its backend kind, source revision, and executable hash must match the request, and its capability identifiers must be safe and unique. Exactly one terminal frame must be last. Version 1 accepts success only when the process exits zero and the terminal reports `succeeded`, `completed-target`, and the declared stop condition. Process success does not imply comparison equality.

On success the new attempt directory contains atomically published `request.json`, `stdout.ndjson`, `stderr.log`, and `replay-manifest.json`. The retained request is canonical, does not add the supervisor's request, executable, or attempt paths, and makes the attempt self-contained for replay. The manifest binds it, the command stream, inputs, backend identity, limits, terminal outcome, and captured artifacts by digest. Its comparison verdict remains `not-run`.

## Deliberate limits

This increment has a synthetic protocol fixture and negative controls for malformed requests, identity mismatch, inherited-secret removal, ordering, terminal endpoint, output cap, timeout/process-tree cleanup, and attempt reuse. It does not yet provide the UI-driving Bosman adapter, retain structured artifacts for failed attempts, enforce cgroup CPU/RAM limits, implement leases, or qualify execution against clean game data. Those remain B1/P01 work.
