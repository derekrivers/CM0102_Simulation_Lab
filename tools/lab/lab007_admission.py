"""Frozen LAB-007 admission; full qualification and accepted precursor evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

spec = importlib.util.spec_from_file_location('lab007_base_admission', Path(__file__).with_name('admission.py'))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
require, canonical, reference = base.require, base.canonical, base.reference
PROFILE, TEMPLATE = 'research-assignment', 'research-retained-assignment-v1'
SELECTED_JOB = '012-retained-assignment'
ACCEPTANCE_SHA = '49e4f1eedfa8216a93a5d75ad9cb7d5f2305f5568c04bf5164cd0d0eac8ae262'
CASE_SHA = '62ea04732223472ccf649eadaba9159b79f550c53dceb6faaa0b84c06eee97e2'
LIMITS = dict(max_jobs=12, elapsed_seconds=600, stall_seconds=120,
              output_bytes=2*1024**2, disk_bytes=512*1024**2,
              min_free_bytes=1024**3, max_attempts=2)
base.LIMITS = LIMITS
base.MAX_PHYSICAL_ATTEMPTS = 26
base.RESERVE_JOB_IDENTITIES = True
base.ATTEMPT_RESERVE = 578*1024**2
base.TOTAL_RESERVE = 26*base.ATTEMPT_RESERVE + base.METADATA_RESERVE


def cases(repo):
    value = json.loads((Path(repo)/'docs/research/LAB_007_CASES_V1.json').read_text())
    rows = [case for job in value['jobs'] for case in job['cases']]
    require(len(value['jobs']) == 12 and len(rows) == 120 and
            hashlib.sha256(canonical(rows)).hexdigest() == CASE_SHA, 'frozen cases changed')
    require(value['jobs'] == [{'job_id': f'{i//10+1:03d}-retained-assignment', 'cases': rows[i:i+10]}
                             for i in range(0, 120, 10)], 'frozen job grouping changed')
    return value['jobs']


def original_jobs(manifest):
    pins = manifest['jobs'][0]['pins']
    return [{'job_id': f'{i:03d}-retained-assignment', 'template_id': TEMPLATE,
             'parameters': {}, 'pins': copy.deepcopy(pins)} for i in range(1, 13)]


def subject(manifest):
    value = copy.deepcopy(manifest)
    value['jobs'] = original_jobs(value)
    value['limits'] = dict(LIMITS)
    value['provenance'].pop('pilot_admission', None)
    value['provenance'].pop('replay_of', None)
    value.pop('campaign_id', None)
    return hashlib.sha256(canonical(value)).hexdigest()


base.subject = subject
reservation = base.reservation


def validate_shape(manifest):
    require(manifest.get('profile_id') == PROFILE and manifest.get('observation_seconds') == 0,
            'wrong LAB-007 profile or observation horizon')
    expected = original_jobs(manifest)
    limits = dict(LIMITS)
    if manifest['provenance'].get('replay_of'):
        expected = [expected[-1]]
    require(manifest['jobs'] == expected and manifest['limits'] == limits, 'matrix/jobs/limits changed')
    require(manifest.get('stop_conditions') == {'max_failures': 1, 'stop_on_divergence': True},
            'stop conditions changed')
    require(manifest['provenance'].get('source_dirty') is False
            and manifest['provenance'].get('case_list_sha256') == CASE_SHA
            and manifest['provenance'].get('selected_replay_job') == SELECTED_JOB, 'frozen provenance changed')


def precursor(ref):
    require(ref.get('sha256') == ACCEPTANCE_SHA, 'unaccepted precursor receipt')
    receipt = base.read_reference(ref)
    require(receipt.get('kind') == 'lab005-006-scientific-acceptance-v1'
            and receipt.get('decision') == 'passed' and receipt.get('reviewer')
            and receipt.get('source_revision') == '70def1244f01bf917aa112ee9e98d5922b864489',
            'precursor acceptance changed')
    require(set(receipt['evidence']) == {'lab005-pilot-v1', 'lab005-pilot-v1-replay-eaf0808b1bf6',
            'lab006-pilot-v1', 'lab006-pilot-v1-replay-8a479a1b4724'}, 'precursor campaigns changed')
    for campaign, evidence in receipt['evidence'].items():
        snapshot = base.read_reference(evidence)
        base._completed(snapshot)
        require(snapshot['campaign']['campaign_id'] == campaign
                and len(snapshot['attempts']) == 1
                and snapshot['attempts'][0]['comparison_verdict'] == 'equal', 'precursor outcome changed')
    return receipt


def validate(manifest, repo):
    validate_shape(manifest)
    cases(repo)
    admission = manifest['provenance'].get('pilot_admission')
    require(isinstance(admission, dict), 'independent operational, qualification and precursor receipts required')
    review = base.read_reference(admission['operational_review'])
    require(review.get('schema_version') == 1 and review.get('kind') == 'research-operational-review-v1'
            and review.get('decision') == 'approved-for-pilot' and review.get('reviewer')
            and review.get('implementation_author') and review['reviewer'] != review['implementation_author'],
            'independent source review required')
    require(review.get('source_revision') == manifest['source_revision']
            and review.get('frozen_subject_sha256') == subject(manifest), 'review subject changed')
    original = copy.deepcopy(manifest)
    original['jobs'], original['limits'] = original_jobs(manifest), dict(LIMITS)
    original['campaign_id'] = review['campaign_id']
    replay = original['provenance'].pop('replay_of', None)
    if replay:
        require(replay == {'campaign_id': review['campaign_id'], 'job_id': SELECTED_JOB,
                           'manifest_sha256': hashlib.sha256(canonical(original)).hexdigest()},
                'only frozen selected job replay is admitted')
    else:
        require(manifest['campaign_id'] == review['campaign_id'], 'reviewed campaign changed')
    base.qualification(admission['qualification_acceptance'])
    precursor(admission['precursor_acceptance'])
    base.clean_source(repo, manifest['source_revision'])
    reservation(manifest)


def build_profile(config, repo, campaign, root, workloads):
    require(root is not None, 'use freeze/admit for LAB-007')
    repo = Path(repo).resolve()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    base.clean_source(repo, revision)
    for key, suffix, ceiling, expected in [
        ('original_executable', None, 7192576, workloads.SPECIMEN_SHA),
        ('retained_capture', 'image.bin', 12000000, workloads.IMAGE_SHA),
        ('retained_capture', 'heap.bin', 120000000, workloads.HEAP_SHA)]:
        path = workloads._path(config, key)
        path = path/suffix if suffix else path
        require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= ceiling,
                'unsupported input extent or symlink')
        require(base.sha(path) == expected, 'unapproved input identity')
    versions = {}
    for key in ('python', 'oracle_python'):
        versions[key] = subprocess.check_output([str(workloads._path(config, key)), '--version'], text=True).strip()
        require(versions[key].startswith('Python 3.12.'), 'qualified Python 3.12 required')
    decoded = subprocess.check_output([str(workloads._path(config, 'oracle_python')), '-I', '-c',
        'import unicorn,capstone; print(unicorn.__version__,capstone.__version__)'], text=True).strip()
    require(decoded == '2.1.4 5.0.7', 'qualified emulator/disassembler required')
    versions.update(unicorn='2.1.4', capstone='5.0.7')
    paths = sorted(set(workloads._files(TEMPLATE, config, repo)))
    pins = [{'path': str(p), 'sha256': base.sha(p)} for p in paths]
    global_paths = [repo/'tools/lab'/name for name in ('core.py', 'workloads.py', 'admission.py',
                    'lab007_admission.py', 'lab.py', 'report.py', 'hold.py', 'Hold-Lab.ps1', 'Lab.ps1', 'Lab.cmd')]
    manifest = {'schema_version': 1, 'campaign_id': campaign, 'profile_id': PROFILE,
        'source_revision': revision, 'observation_seconds': 0,
        'pins': [{'path': str(p), 'sha256': base.sha(p)} for p in global_paths],
        'jobs': [{'job_id': j['job_id'], 'template_id': TEMPLATE, 'parameters': {}, 'pins': pins} for j in cases(repo)],
        'limits': dict(LIMITS), 'stop_conditions': {'max_failures': 1, 'stop_on_divergence': True},
        'provenance': {'config_sha256': workloads._config_digest(config), 'source_dirty': False,
            'tool_versions': versions, 'research_protocol': 'docs/research/LAB_007_ADMISSION_V1.md',
            'research_state_root': str(Path(root).resolve()), 'case_list_sha256': CASE_SHA,
            'selected_replay_job': SELECTED_JOB, 'production_admission': 'none'}}
    validate_shape(manifest)
    return manifest
