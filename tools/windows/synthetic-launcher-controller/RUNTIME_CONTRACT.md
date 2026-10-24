# Synthetic launcher runtime contract

`config/synthetic-launcher-controller-runtime-v1.json` freezes the next
implementation boundary while every new production image remains unbound. Its
exact schema is `config/synthetic-launcher-controller-runtime-v1.schema.json`,
and `config/synthetic-launcher-controller-report-v1.schema.json` freezes the
privacy-safe report grammar. These files add no Windows production image,
controller/native/UI authority, private configuration, retained-run harness, or
fixture/game process-creation route. Verify mode invokes only fixed Git read
operations needed to bind the source revision; self-test additionally starts a
fixed `/usr/bin/python3` copy check and requires that copied verifier to fail.
Successful verification binds the exact committed blobs and rejects changes
observed across its two reads, but it does not lease the mutable checkout after
return. Downstream build work must consume the named Git commit or a separately
held immutable snapshot, never assume the working tree remains protected.

The runtime contract keeps the accepted UI fixture unchanged, gives the timeout
root and child their own fixed images, routes locked-desktop refusal through a
separate image with no launch capability, and requires a fixed-target outer
supervisor Job around the controller. It also freezes the exact cross-attempt
semantic projection before evidence exists. The contract state is
`build-unpinned`; live run mode must reject it before any process-creation call.
Its report schema accepts only minimal ineligible not-run errors; the reviewed
pinned control transition must add the full-report route and its implications.
The later controller/no-UI build revision and the still-later image-pinning
revision each require independent exact-revision review before the first live
fixture attempt.

Verify the commit-bound runtime profile, exact profile schema, report schema,
accepted input identities, fixed scenario mapping, comparison projection, and
fail-closed status with:

```sh
python3 tools/windows/synthetic-launcher-controller/verify_controller_runtime_contract.py self-test
python3 tools/windows/synthetic-launcher-controller/verify_controller_runtime_contract.py verify \
  --repo "$PWD" --source-commit "$(git rev-parse HEAD)"
```
