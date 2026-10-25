"""Readable private local reports; no hypothesis or phase-gate promotion."""
from collections import Counter
import datetime
import html
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import quote


def escape(value):
    return html.escape(str(value), quote=True)


def timestamp(value):
    if value is None:
        return "unavailable"
    return datetime.datetime.fromtimestamp(value, datetime.timezone.utc).isoformat()


def resources(attempts):
    cpu_seconds, peak_bytes, measured = 0.0, 0, 0
    for attempt in attempts:
        details = (attempt.get("result") or {}).get("details", {})
        before, after = details.get("resources_before", {}), details.get("resources_after", {})
        try:
            first = dict(line.split() for line in before["cpu.stat"].splitlines())
            last = dict(line.split() for line in after["cpu.stat"].splitlines())
            cpu_seconds += max(0, int(last["usage_usec"]) - int(first["usage_usec"])) / 1_000_000
            peak_bytes = max(peak_bytes, int(after.get("memory.peak", 0)))
            measured += 1
        except (KeyError, ValueError, TypeError):
            pass
    return f"{cpu_seconds:.3f} CPU seconds across {measured} measured attempts; service lifetime peak memory {peak_bytes / 1024**2:.1f} MiB. Interrupted attempts may lack a final sample."


def write_report(root, campaign_id, snapshot):
    from core import atomic_json
    campaign = snapshot["campaign"]
    manifest = campaign["manifest"]
    destination = Path(root) / "campaigns" / campaign_id
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    jobs = snapshot["jobs"]
    attempts = snapshot["attempts"]
    counts = Counter(job["state"] for job in jobs)
    verdicts = Counter(job["comparison_verdict"] for job in jobs)
    horizon = manifest.get("observation_seconds", 0)
    elapsed = campaign.get("observation_elapsed_seconds", 0)
    if not elapsed and campaign.get("observation_started"):
        # Wall age is informational only; it cannot establish elapsed qualification.
        elapsed_text = "See durable monotonic observation events; wall age is not qualification evidence."
    else:
        elapsed_text = f"{elapsed:.3f} seconds recorded"
    rows = []
    evidence_classes = {"synthetic-progress-v1": "Synthetic engineering control",
                        "rng-native-wasm-v1": "Repeated qualified regression",
                        "original-r10-regression-v1": "Repeated qualified regression",
                        "bosman-same-save-v1": "Repeated qualified regression",
                        "research-squad-members-v1": "New structural observation; review required"}
    for job in jobs:
        spec = job["spec"] if isinstance(job["spec"], dict) else {}
        template = spec.get("template_id")
        template = template if isinstance(template, str) else "invalid"
        rows.append("<tr>" + "".join("<td>" + escape(value) + "</td>" for value in (
            job["job_id"], template,
            evidence_classes.get(template, "Unsupported / rejected"),
            job["state"], job["comparison_verdict"], job.get("reason") or "",
            job.get("attempts", 0))) + "</tr>")
    attempt_rows = []
    for attempt in attempts:
        directory = Path(attempt["directory"])
        relative = quote(os.path.relpath(directory, destination).replace(os.sep, "/"), safe="/.-_")
        links = []
        for name in ("request.json", "result.json", "stdout.log", "stderr.log"):
            if (directory / name).is_file():
                links.append(f'<a href="{relative}/{name}">{name}</a>')
        result = attempt.get("result") or {}
        details = result.get("details", {})
        duration = ((attempt.get("finished") or datetime.datetime.now(datetime.timezone.utc).timestamp())
                    - attempt["started"])
        attempt_rows.append("<tr>" + "".join("<td>" + escape(value) + "</td>" for value in (
            attempt["attempt_id"], attempt["job_id"], attempt["ordinal"],
            attempt["execution_status"], attempt["comparison_verdict"],
            attempt.get("reason") or "", f"{duration:.3f}s",
            attempt.get("publication_state", "unknown")))
            + "<td>" + " · ".join(links) + "</td><td><pre>"
            + escape(json.dumps(details, indent=2)) + "</pre></td></tr>")
    events = "".join("<tr>" + "".join("<td>" + escape(value) + "</td>" for value in (
        timestamp(event["time"]), event["kind"], event.get("job_id") or "",
        json.dumps(event["detail"], sort_keys=True))) + "</tr>" for event in snapshot["events"])
    provenance = manifest.get("provenance", {})
    limitations = [
        "This is the bounded single-PC/WSL local lab. Full P01 and P03 remain open.",
        "Execution completion and comparison equality are separate. Rejected, failed and censored work stays in the denominator.",
        "Regression reruns supply repeatability evidence; they do not create new game-semantics discoveries.",
        "Squad membership interpretation and failed R9b file-use provenance remain open. Hypotheses require independent review.",
        "Private reports and retained artifacts may contain private inputs; keep the state directory outside Git and public build output.",
        "The WSL worker survives closing the agent/chat; PC shutdown, suspend or WSL shutdown interrupts execution and requires recovery.",
    ]
    document = f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>CM0102 lab — {escape(campaign_id)}</title>
<style>body{{font:16px system-ui,sans-serif;max-width:1500px;margin:2rem auto;padding:0 1rem;color:#17232e;background:#f7f9fb}}h1,h2{{color:#173e55}}table{{border-collapse:collapse;width:100%;background:white;margin:1rem 0}}th,td{{text-align:left;vertical-align:top;border:1px solid #c9d5dd;padding:.5rem}}th{{background:#e8f0f5}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;max-width:40rem;margin:0}}.card{{background:white;border-left:5px solid #29738d;padding:1rem;margin:1rem 0}}a{{color:#075e91}}code{{overflow-wrap:anywhere}}</style>
<h1>CM0102 local research campaign</h1>
<div class="card"><strong>{escape(campaign_id)} — {escape(campaign['state'])}</strong>
<p>Observation qualification: {escape('censored / not qualified' if campaign.get('observation_qualified',1)==0 else 'eligible; full milestone still requires independent acceptance')}. Stop reason: {escape(campaign.get('stop_reason') or 'none')}.</p>
<p>{len(jobs)} requested job records; {len(attempts)} physical attempts.</p>
<p>Execution: {escape(dict(counts))}<br>Comparison: {escape(dict(verdicts))}</p>
<p>Revision: <code>{escape(manifest['source_revision'])}</code><br>
Manifest SHA-256: <code>{escape(campaign['manifest_sha256'])}</code></p>
<p>Created {escape(timestamp(campaign['created']))}; report refreshed {escape(datetime.datetime.now(datetime.timezone.utc).isoformat())}.</p>
<p>Observation target: {horizon} seconds. {escape(elapsed_text)}<br>
Recorded active execution: {campaign.get('active_seconds',0):.3f}s; explicit idle queue: {campaign.get('idle_seconds',0):.3f}s.
Interrupted/unaccounted intervals are retained in recovery events and cannot be called active execution.</p>
<p>{escape(resources(attempts))}</p>
<p><a href="manifest.json">Frozen manifest</a> · <a href="report.json">Machine-readable report</a></p></div>
<h2>Requested jobs</h2><table><tr><th>Logical job</th><th>Approved template</th><th>Evidence class</th><th>Execution</th><th>Comparison</th><th>Reason</th><th>Attempts</th></tr>{''.join(rows)}</table>
<h2>Immutable physical attempts and retained evidence</h2><table><tr><th>Attempt</th><th>Job</th><th>Ordinal</th><th>Execution</th><th>Comparison</th><th>Reason</th><th>Elapsed</th><th>Publication</th><th>Artifacts</th><th>Observations / resources / limitations</th></tr>{''.join(attempt_rows)}</table>
<h2>Frozen resource budgets and stop conditions</h2><pre>{escape(json.dumps({'limits':manifest['limits'],'stop_conditions':manifest['stop_conditions'],'worker':{'CPUQuota':'100%','MemoryMax':'2 GiB','MemorySwapMax':0,'TasksMax':128}},indent=2))}</pre>
<h2>Provenance and research boundaries</h2><pre>{escape(json.dumps(provenance,indent=2))}</pre>
<h2>Failures, recovery and queue accounting</h2><table><tr><th>UTC</th><th>Event</th><th>Job</th><th>Detail</th></tr>{events}</table>
<h2>Limitations and unresolved questions</h2><ul>{''.join('<li>'+escape(item)+'</li>' for item in limitations)}</ul>
<p>Review a selected result with the Windows launcher: <code>Lab.cmd replay JOB_ID</code>.
Replay preserves the original and creates a separately identified campaign. Changed inputs/tools/source reject rather than silently changing the experiment.</p>
</html>'''
    atomic_json(destination / "report.json", snapshot)
    fd, temporary = tempfile.mkstemp(dir=destination, prefix=".report-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(document)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination / "report.html")
        directory = os.open(destination, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination / "report.html"
