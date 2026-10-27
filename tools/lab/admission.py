"""Private, fail-closed LAB-005/006 admission. No evidence is auto-approved.

Receipts are human/independent-agent attestations in the local trust boundary,
not cryptographic proof of reviewer identity. Their immutable digests and the
underlying evidence are checked on admission and every physical attempt.
"""
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

QUALIFICATION_SOURCE = '42a313887e46274a2932dbe8c04de7a5e8f2840d'
QUALIFICATION_ID = 'll1-24h-20261025'
QUALIFICATION_SHA = '0ac601252e55b485f5305d433c5f6c68c9d11e64cf07034f2488907061c3d711'
RNG_SHA = '1c8d5c5b3443386e18f2124f19dcebbde7999124e3b557b71f78507597ce0d16'
RNG_JOB = '001-rng-native-wasm-v1'
LIMITS = dict(max_jobs=1, elapsed_seconds=300, stall_seconds=120,
              output_bytes=2*1024**2, disk_bytes=64*1024**2,
              min_free_bytes=1024**3, max_attempts=2)
# Four physical attempts = pilot + one selected replay, each with one recovery.
# Extra margin covers sampled disk overshoot; it is not a filesystem quota.
ATTEMPT_RESERVE = LIMITS['disk_bytes'] + LIMITS['output_bytes'] + 64*1024**2
METADATA_RESERVE = 16*1024**2
MAX_PHYSICAL_ATTEMPTS = 4
RESERVE_JOB_IDENTITIES = False
TOTAL_RESERVE = MAX_PHYSICAL_ATTEMPTS*ATTEMPT_RESERVE + METADATA_RESERVE


def require(condition, reason):
    if not condition:
        raise ValueError('Research admission: ' + reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def reference(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': sha(path)}


def read_reference(ref):
    require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'missing evidence reference')
    path = Path(ref['path'])
    require(path.is_absolute() and path.is_file() and not path.is_symlink(), 'invalid evidence path')
    require(sha(path) == ref['sha256'], 'changed evidence')
    return json.loads(path.read_text())


def subject(manifest):
    value = copy.deepcopy(manifest)
    value['provenance'].pop('pilot_admission', None)
    value['provenance'].pop('replay_of', None)
    value.pop('campaign_id', None)
    return hashlib.sha256(canonical(value)).hexdigest()


def clean_source(repo, revision):
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo,
                                    text=True).strip() == revision, 'source revision changed')
    require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo,
                                        text=True), 'research source must be clean')


def validate_shape(manifest):
    choices = {'research-anomalies': 'research-squad-anomalies-v1',
               'research-consumers': 'research-member-consumers-v1'}
    template = choices.get(manifest.get('profile_id'))
    require(template is not None, 'unknown pilot profile')
    require(manifest.get('limits') == LIMITS, 'pilot resource ceilings changed')
    require(manifest.get('observation_seconds', 0) == 0, 'pilot cannot borrow observation horizon')
    require(manifest.get('stop_conditions') == {'max_failures': 1, 'stop_on_divergence': True},
            'pilot stop policy changed')
    jobs = manifest.get('jobs', [])
    require(len(jobs) == 1 and jobs[0].get('template_id') == template
            and jobs[0].get('job_id') == '001-' + template
            and jobs[0].get('parameters') == {}, 'pilot must contain exactly its frozen job')
    require(manifest['provenance'].get('source_dirty') is False, 'dirty source cannot be admitted')


def _completed(data):
    campaign = data['campaign']
    require(campaign['state'] == 'completed' and not campaign.get('stop_reason'), 'campaign not completed')
    require(campaign['manifest_sha256'] == hashlib.sha256(canonical(campaign['manifest'])).hexdigest(),
            'snapshot manifest identity mismatch')
    pins = campaign['manifest']['pins'] + [p for j in campaign['manifest']['jobs'] for p in j.get('pins', [])]
    for pin in pins:
        require(sha(pin['path']) == pin['sha256'], 'qualification source/input/tool pin changed')
    sources = [Path(p['path']).resolve().parents[2] for p in pins
               if Path(p['path']).parts[-3:] == ('tools', 'lab', 'core.py')]
    require(len(set(sources)) == 1, 'qualification source checkout missing')
    clean_source(sources[0], campaign['manifest']['source_revision'])
    roots = {Path(a['directory']).parent.parent for a in data['attempts']}
    require(len(roots) == 1, 'qualification state root missing')
    config = json.loads((next(iter(roots))/'config.json').read_text())
    config_bytes = json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    require(hashlib.sha256(config_bytes).hexdigest() == campaign['manifest']['provenance']['config_sha256'],
            'qualification configuration changed')
    require(all(j['state'] == 'succeeded' and j['execution_status'] == 'succeeded'
                for j in data['jobs']), 'unsuccessful qualification job')
    completed = [e['time'] for e in data['events'] if e['kind'] == 'completed']
    require(bool(completed), 'completion event missing')
    require(not any(e['kind'] in ('observation-gap', 'stop-condition')
                    for e in data['events']), 'qualification evidence requires failure disposition')
    for attempt in data['attempts']:
        require(attempt['publication_state'] == 'published' and attempt['finished'] is not None,
                'attempt publication incomplete')
        directory = Path(attempt['directory'])
        result = attempt['result']
        require((directory/'result.json').read_bytes() == canonical(result) + b'\n',
                'attempt result publication changed')
        actual = []
        for path in sorted(directory.rglob('*')):
            require(not path.is_symlink(), 'artifact symlink')
            if path.is_file() and path.name != 'result.json' and '.pending-' not in path.name:
                actual.append({'path': str(path.relative_to(directory)), 'sha256': sha(path),
                               'byte_count': path.stat().st_size})
        require(actual == result['details']['artifacts'], 'attempt inventory changed')
    return max(completed)


def qualification(ref):
    receipt = read_reference(ref)
    require(receipt.get('schema_version') == 1 and receipt.get('kind') == 'qualification-acceptance-v1'
            and receipt.get('decision') == 'passed', 'qualification not independently accepted')
    require(receipt.get('reviewer') and receipt.get('implementation_author')
            and receipt['reviewer'] != receipt['implementation_author'], 'qualification reviewer must be independent')
    require((receipt.get('source_revision'), receipt.get('campaign_id'), receipt.get('manifest_sha256'),
             receipt.get('selected_job_id')) == (QUALIFICATION_SOURCE, QUALIFICATION_ID, QUALIFICATION_SHA, RNG_JOB),
            'wrong qualification identity')
    evidence = receipt['evidence']
    original = read_reference(evidence['completion_snapshot'])
    require(read_reference(evidence['completion_report']) == original, 'report differs from completion snapshot')
    replay = read_reference(evidence['replay_snapshot'])
    require(read_reference(evidence['replay_manifest']) == replay['campaign']['manifest'], 'replay manifest mismatch')
    end = _completed(original)
    replay_end = _completed(replay)
    c, r = original['campaign'], replay['campaign']
    require((c['campaign_id'], c['manifest_sha256'], c['manifest']['source_revision']) ==
            (QUALIFICATION_ID, QUALIFICATION_SHA, QUALIFICATION_SOURCE), 'wrong completion campaign')
    require(c['manifest'].get('observation_seconds') == 86400 and c.get('observation_qualified') == 1
            and c.get('observation_elapsed_seconds', 0) >= 86400, 'actual qualification horizon incomplete')
    require(end >= 1793026605 and end >= c['observation_started'] + 86400,
            'qualification completion precedes its horizon')
    require({j['job_id'] for j in original['jobs']} ==
            {RNG_JOB, '002-original-r10-regression-v1', '003-bosman-same-save-v1'}, 'qualification jobs changed')
    r10 = [a for a in original['attempts'] if a['job_id'] == '002-original-r10-regression-v1'
           and a['execution_status'] == 'succeeded']
    bosman = [a for a in original['attempts'] if a['job_id'] == '003-bosman-same-save-v1'
              and a['execution_status'] == 'succeeded']
    require(len(r10) == len(bosman) == 1 and r10[0]['comparison_verdict'] == 'equal'
            and bosman[0]['comparison_verdict'] == 'not-run', 'qualification reference endpoints incomplete')
    facts = r10[0]['result']['details']
    require(facts.get('successful_calls') == 11 and facts.get('censored_calls') == 4
            and len(facts.get('controls', {})) == 12 and all(facts['controls'].values()), 'R10 controls changed')
    require(bosman[0]['result']['details'].get('endpoint') == 'classic-same-save-normal-again-14-days-equal',
            'Bosman endpoint changed')
    require(r['manifest'].get('observation_seconds') == 0
            and r['manifest']['source_revision'] == QUALIFICATION_SOURCE
            and r['manifest']['provenance']['replay_of'] ==
            {'campaign_id': QUALIFICATION_ID, 'job_id': RNG_JOB, 'manifest_sha256': QUALIFICATION_SHA},
            'wrong selected replay provenance')
    require(len(replay['jobs']) == 1 and replay['jobs'][0]['job_id'] == RNG_JOB
            and r['observation_started'] >= end, 'replay must start after actual completion')
    original_job = next(j for j in original['jobs'] if j['job_id'] == RNG_JOB)
    require(replay['jobs'][0]['spec'] == original_job['spec'], 'replay selected job changed')
    for data in (original, replay):
        attempts = [a for a in data['attempts'] if a['job_id'] == RNG_JOB and a['execution_status'] == 'succeeded']
        require(len(attempts) == 1 and attempts[0]['comparison_verdict'] == 'equal', 'RNG replay not equal')
        facts = attempts[0]['result']['details']
        require(facts.get('native_sha256') == facts.get('wasm_sha256') == RNG_SHA
                and facts.get('canonical_bytes') == 75952
                and facts.get('negative_control_mismatches') == [1023, 61, 2447, 123], 'RNG scientific endpoint changed')
        for filename in ('native.stdout', 'wasm.bin'):
            path = Path(attempts[0]['directory'])/filename
            require(path.stat().st_size == 75952 and sha(path) == RNG_SHA, 'raw RNG replay changed')
    observed = datetime.datetime.fromisoformat(receipt['observed_at_utc'].replace('Z', '+00:00'))
    require(observed.tzinfo is not None and observed.timestamp() >= replay_end, 'acceptance predates replay completion')
    return receipt


def validate(manifest, repo):
    validate_shape(manifest)
    admission = manifest['provenance'].get('pilot_admission')
    require(isinstance(admission, dict), 'Research release blocked: independent receipts are required')
    review = read_reference(admission['operational_review'])
    require(review.get('schema_version') == 1 and review.get('kind') == 'research-operational-review-v1'
            and review.get('decision') == 'approved-for-pilot', 'operational source review not approved')
    require(review.get('reviewer') and review.get('implementation_author')
            and review['reviewer'] != review['implementation_author'], 'source reviewer must be independent')
    require(review.get('source_revision') == manifest['source_revision']
            and review.get('frozen_subject_sha256') == subject(manifest), 'operational review subject changed')
    replay = manifest['provenance'].get('replay_of')
    if replay:
        original = copy.deepcopy(manifest)
        original['campaign_id'] = review['campaign_id']
        original['provenance'].pop('replay_of')
        require(replay == {'campaign_id': review['campaign_id'], 'job_id': manifest['jobs'][0]['job_id'],
                           'manifest_sha256': hashlib.sha256(canonical(original)).hexdigest()},
                'research replay differs from reviewed pilot')
    else:
        require(manifest['campaign_id'] == review['campaign_id'], 'reviewed campaign changed')
    qualification(admission['qualification_acceptance'])
    clean_source(repo, manifest['source_revision'])
    reservation(manifest, create=False)


def _atomic(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical(value) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def reservation(manifest, create=False, attempt=None):
    """Reserve pilot+replay growth now; release each attempt's allocation once.

    Journal-before-truncate makes restart idempotent. The real worker holds its
    cross-root heavy lock before consumption. A second private flock also fences
    freeze/admission callers. Unused space stays allocated for retained replay.
    """
    import fcntl
    root = Path(manifest['provenance']['research_state_root'])
    require(root.is_absolute() and str(root.resolve()) == str(root)
            and not str(root).startswith('/mnt/'), 'private native Linux state root required')
    directory = root/'research-reservations'
    if create:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(directory.is_dir(), 'disk reservation missing')
    key = subject(manifest)
    record, allocation = directory/(key+'.json'), directory/(key+'.reserve')
    with (directory/(key+'.lock')).open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not record.exists():
            require(create and not allocation.exists(), 'incomplete reservation requires inspection')
            require(shutil.disk_usage(root).free >= TOTAL_RESERVE + LIMITS['min_free_bytes'], 'insufficient reserved disk')
            with allocation.open('xb') as stream:
                os.chmod(allocation, 0o600)
                os.posix_fallocate(stream.fileno(), 0, TOTAL_RESERVE)
                os.fsync(stream.fileno())
            _atomic(record, {'schema_version': 1, 'subject_sha256': key, 'total_bytes': TOTAL_RESERVE,
                             'per_attempt_bytes': ATTEMPT_RESERVE, 'consumed': {}})
        data = json.loads(record.read_text())
        require(data['subject_sha256'] == key and data['total_bytes'] == TOTAL_RESERVE
                and data['per_attempt_bytes'] == ATTEMPT_RESERVE, 'reservation identity changed')
        consumed = data['consumed']
        require(isinstance(consumed, dict) and len(consumed) <= MAX_PHYSICAL_ATTEMPTS, 'invalid consumed reservation')
        if attempt is not None:
            require(Path(attempt['directory']).resolve().is_relative_to(root/'attempts'),
                    'attempt outside reserved state root')
            identity = {'campaign_id': attempt['campaign_id'], 'ordinal': attempt['ordinal']}
            if RESERVE_JOB_IDENTITIES:
                require(attempt.get('job_id') in {j['job_id'] for j in manifest['jobs']}, 'unreserved job')
                identity['job_id'] = attempt['job_id']
                require(not any(value == identity and key != attempt['attempt_id'] for key, value in consumed.items()),
                        'duplicate job attempt ordinal')
            require(1 <= attempt['ordinal'] <= 2, 'attempt budget exceeded')
            role = 'replay_campaign' if manifest['provenance'].get('replay_of') else 'pilot_campaign'
            require(data.get(role, attempt['campaign_id']) == attempt['campaign_id'], 'only one pilot and one replay are reserved')
            data[role] = attempt['campaign_id']
            if attempt['attempt_id'] not in consumed:
                require(len(consumed) < MAX_PHYSICAL_ATTEMPTS, 'pilot and selected replay reservation exhausted')
                consumed[attempt['attempt_id']] = identity
                _atomic(record, data)
            require(consumed[attempt['attempt_id']] == identity, 'reservation attempt identity changed')
        remaining = TOTAL_RESERVE - len(consumed)*ATTEMPT_RESERVE
        require(0 <= len(consumed) <= MAX_PHYSICAL_ATTEMPTS and allocation.is_file() and not allocation.is_symlink(), 'invalid reservation')
        require(allocation.stat().st_size >= remaining, 'reserved bytes missing')
        require(allocation.stat().st_blocks * 512 >= allocation.stat().st_size, 'reservation is sparse or unallocated')
        # A journaled consume may have been interrupted before truncation.
        if attempt is not None:
            with allocation.open('r+b') as stream:
                stream.truncate(remaining)
                os.fsync(stream.fileno())
        require(shutil.disk_usage(root).free >= LIMITS['min_free_bytes'], 'free-space floor unavailable')
        return {'subject_sha256': key, 'reserved_bytes': remaining, 'consumed_attempts': len(consumed),
                'pilot_and_replay_attempts': MAX_PHYSICAL_ATTEMPTS, 'path': str(allocation)}
