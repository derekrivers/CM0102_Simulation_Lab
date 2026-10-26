"""Frozen approved workload adapters; manifest arguments never become shell commands."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

TEMPLATES = {'synthetic-progress-v1', 'rng-native-wasm-v1', 'original-r10-regression-v1',
             'bosman-same-save-v1', 'research-squad-members-v1',
             'research-squad-anomalies-v1', 'research-member-consumers-v1'}
# Ordinary start remains blocked. Only frozen, independently reviewed pilot
# manifests with accepted qualification evidence can enter the controlled route.
RESEARCH_CANDIDATES = {
    'research-anomalies': {'campaign': 'LAB-005', 'template': 'research-squad-anomalies-v1',
                           'protocol': 'docs/research/LAB_005_V1.md'},
    'research-consumers': {'campaign': 'LAB-006', 'template': 'research-member-consumers-v1',
                          'protocol': 'docs/research/LAB_006_V1.md'},
}
RESEARCH_RELEASE_BLOCKER = ('Research release blocked: use freeze then admit with exact operational '
                            'review and completed qualification/replay acceptance. Pilot resource '
                            'measurement and selected-result raw review follow admission.')


def admission_module():
    # Also works under python -I, which excludes the script directory from sys.path.
    spec = importlib.util.spec_from_file_location('research_admission', Path(__file__).with_name('admission.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_research(manifest):
    return any(job.get('template_id') in {c['template'] for c in RESEARCH_CANDIDATES.values()}
               for job in manifest.get('jobs', []) if isinstance(job, dict))


def ensure_released_profile(profile):
    if profile in RESEARCH_CANDIDATES:
        raise ValueError(RESEARCH_RELEASE_BLOCKER)


def research_readiness(repo_root):
    """Read source identities only. Never read private inputs or start a worker."""
    repo = Path(repo_root)
    rows = []
    for profile, candidate in RESEARCH_CANDIDATES.items():
        protocol = repo / candidate['protocol']
        rows.append({**candidate, 'profile': profile, 'execution_approved': False,
                     'executed': False, 'independently_accepted': False,
                     'planned_jobs': 1, 'physical_attempts': 0,
                     'protocol_sha256': sha(protocol), 'blocker': RESEARCH_RELEASE_BLOCKER,
                     'proposed_limits': {'elapsed_seconds': 300, 'stall_seconds': 120,
                                         'output_bytes': 2*1024**2, 'disk_bytes': 64*1024**2,
                                         'min_free_bytes': 1024**3, 'max_attempts': 2}})
    case_file = repo / 'docs/research/LAB_007_CASES_V1.json'
    rows.append({'campaign': 'LAB-007', 'profile': None, 'execution_approved': False,
                 'executed': False, 'independently_accepted': False,
                 'planned_cases': 120, 'planned_jobs': 12, 'unstarted_cases': 120,
                 'case_file_sha256': sha(case_file),
                 'blocker': 'LAB-005/LAB-006 raw evidence and R10 extension admission require independent review; no executable adapter admitted.'})
    return rows
RNG_SHA = '1c8d5c5b3443386e18f2124f19dcebbde7999124e3b557b71f78507597ce0d16'
IMAGE_SHA = 'ae11ce3ef6267ad55be6aa6387f676704b1bb8a6310507db6c5ccfe494d45c3a'
HEAP_SHA = '30ee2baefad8f57f8760f30abc076586f2d13339bb1629f75346a5dcbc1357a0'
SPECIMEN_SHA = '0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86'

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def _config_digest(config):
    return hashlib.sha256(canonical(config or {})).hexdigest()

def _path(config, key):
    value = (config or {}).get(key, sys.executable if key == 'python' else None)
    require(isinstance(value, str) and Path(value).is_absolute(), 'missing absolute config path: '+key)
    path = Path(value).absolute()
    require(path.exists(), 'configured path unavailable: '+key)
    return path

def _files(template, config, repo):
    result = [repo/'tools/lab/workloads.py', _path(config, 'python')]
    if template == 'research-squad-anomalies-v1':
        capture = _path(config, 'retained_capture')
        result += [capture/'image.bin', capture/'heap.bin', repo/'docs/research/LAB_005_V1.md']
        result += [repo/'scripts'/name for name in ('lab005.py', 'lab005_decoder_a.py', 'lab005_decoder_b.py', 'lab005_tests.py')]
    elif template == 'research-member-consumers-v1':
        result += [_path(config, key) for key in ('oracle_python', 'original_executable')]
        result += [repo/'scripts/lab006.py', repo/'scripts/lab006_test.py', repo/'docs/research/LAB_006_V1.md',
                   repo/'docs/research/evidence/pc-r10-command-static-v1.json']
        venv = _path(config, 'oracle_python').parent.parent
        result += [venv/'pyvenv.cfg']
        directory = venv/'lib/python3.12/site-packages/capstone'
        require(directory.is_dir(), 'qualified disassembler package unavailable')
        result += [p for p in directory.rglob('*') if p.is_file() and (p.suffix == '.py' or '.so' in p.name)]
    elif template == 'rng-native-wasm-v1':
        result += [_path(config, k) for k in ('node', 'rng_native', 'rng_wasm')]
        result += [repo/'scripts/r1/run_wasm.mjs', repo/'crates/cm-rng/fixtures/corpus.bin']
    elif template in ('original-r10-regression-v1', 'research-squad-members-v1'):
        capture = _path(config, 'retained_capture')
        result += [capture/'image.bin', capture/'heap.bin']
        if template == 'research-squad-members-v1':
            result += [repo/'docs/research/LOCAL_LAB_RESEARCH_V1.md']
        if template == 'original-r10-regression-v1':
            result += [_path(config, k) for k in ('oracle_python', 'original_executable')]
            result += [repo/'scripts'/name for name in ('qualify_pc_r10_command.py',
                       'qualify_human_registry.py', 'qualify_manager_bound_plan.py')]
            venv = _path(config, 'oracle_python').parent.parent
            result += [venv/'pyvenv.cfg']
            for module in ('unicorn', 'capstone'):
                directory = venv/'lib/python3.12/site-packages'/module
                require(directory.is_dir(), 'qualified oracle package unavailable')
                result += [p for p in directory.rglob('*') if p.is_file() and
                           (p.suffix == '.py' or '.so' in p.name)]
            result += [repo/'config/upstream-lock.json',
                       repo/'docs/research/evidence/pc-r10-command-retained-oracle-v1.json']
    elif template == 'bosman-same-save-v1':
        result += [_path(config, k) for k in ('bosman_supervisor','bosman_adapter','bosman_config','bosman_request')]
        backend = json.loads(_path(config, 'bosman_config').read_text())
        result += [Path(backend[k]).resolve(strict=True) for k in
                   ('python_executable','smoke_runner','bosman_executable','clean_manifest')]
    return [p.resolve(strict=True) for p in result]

def _pin_map(manifest, job=None):
    pins = list(manifest.get('pins', [])) + ([] if job is None else job.get('pins', []))
    out = {}
    for pin in pins:
        require(set(pin) == {'path','sha256'}, 'invalid pin fields')
        path = str(Path(pin['path']).resolve(strict=True))
        require(path not in out or out[path] == pin['sha256'], 'conflicting pins')
        out[path] = pin['sha256']
    return out

def validate(manifest, repo_root, config=None):
    """Global policy; bad individual jobs are accounted as rejected."""
    require(manifest.get('schema_version') == 1, 'unsupported manifest schema')
    if is_research(manifest):
        admission_module().validate(manifest, repo_root)
    require(manifest.get('provenance', {}).get('config_sha256') == _config_digest(config),
            'local configuration changed; freeze a new campaign')
    pins = _pin_map(manifest)
    own = Path(repo_root).resolve()/'tools/lab/workloads.py'
    require(str(own) in pins and pins[str(own)] == sha(own), 'workload source must be pinned')
    for path, digest in pins.items():
        require(Path(path).is_file() and sha(path) == digest, 'global pin mismatch')

def validate_job(manifest, job, repo_root, config=None):
    template, params = job.get('template_id'), job.get('parameters', {})
    require(template in TEMPLATES, 'unapproved template')
    if template in {item['template'] for item in RESEARCH_CANDIDATES.values()}:
        admission_module().validate(manifest, repo_root)
        require(job == manifest['jobs'][0], 'research job differs from frozen pilot')
    require(isinstance(params, dict), 'parameters must be object')
    if template == 'synthetic-progress-v1':
        require(set(params) <= {'steps','delay_ms','mode'}, 'unknown synthetic parameter')
        for key,low,high,default in [('steps',1,1000,3),('delay_ms',0,1000,10)]:
            require(type(params.get(key,default)) is int and low<=params.get(key,default)<=high, 'synthetic bound: '+key)
        require(params.get('mode','normal') in {'normal','fail','stall','output','child-orphan'}, 'unknown synthetic mode')
    else:
        require(not params, 'frozen template accepts no parameters')
    pins = _pin_map(manifest, job)
    for path in _files(template, config, Path(repo_root).resolve()):
        require(path.is_file() and str(path) in pins and pins[str(path)] == sha(path), 'template input/tool not pinned')
    if template in ('original-r10-regression-v1','research-squad-members-v1','research-squad-anomalies-v1'):
        capture = _path(config,'retained_capture')
        require(sha(capture/'image.bin')==IMAGE_SHA and sha(capture/'heap.bin')==HEAP_SHA, 'unapproved retained capture')
        if template=='original-r10-regression-v1':
            require(sha(_path(config,'original_executable'))==SPECIMEN_SHA, 'unapproved original specimen')
    if template == 'research-member-consumers-v1':
        require(sha(_path(config,'original_executable'))==SPECIMEN_SHA, 'unapproved original specimen')
    if template=='bosman-same-save-v1':
        request=json.loads(_path(config,'bosman_request').read_text())
        commands=request.get('commands',[])
        require(len(commands)==1 and commands[0].get('kind')=='bosman-classic-same-save-v1', 'unapproved Bosman command')
        p=commands[0]['parameters']
        require({k:p.get(k) for k in ('mode','days','jobs','runs','seed','fixed_clock','expected_save_relation')} ==
                dict(mode='classic',days=14,jobs=2,runs=['normal','again'],seed=1,fixed_clock=True,expected_save_relation='byte-identical'),
                'Bosman campaign widening rejected')
        require(request.get('expected_stop_condition')=='classic-same-save-normal-again-14-days-equal', 'unapproved Bosman endpoint')
        require(request.get('backend',{}).get('kind')=='bosman-native','unapproved backend')

def prepare(manifest, job, attempt_dir, repo_root, config=None):
    validate(manifest,repo_root,config)
    validate_job(manifest,job,repo_root,config)
    attempt=Path(attempt_dir).resolve()
    task={'template_id':job['template_id'],'parameters':job.get('parameters',{}),'config':config or {},
          'repo_root':str(Path(repo_root).resolve()),'attempt_dir':str(attempt),'job_id':job['job_id'],
          'manifest':manifest,'job':job}
    path=attempt/'workload-task.json'
    with path.open('x') as stream:
        json.dump(task,stream)
    path.chmod(0o600)
    return {'argv':[str(_path(config,'python')),'-I',str(Path(repo_root).resolve()/'tools/lab/workloads.py'),'_execute',str(path)],
            'cwd':str(attempt),'env':{'TZ':'UTC','LANG':'C','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1'},
            'progress_file':str(attempt/'progress.json'),'comparison_file':str(attempt/'workload-result.json')}

def result(manifest,job,attempt_dir,returncode):
    path=Path(attempt_dir)/'workload-result.json'
    if not path.is_file():
        return {'execution_status':'failed' if returncode else 'infrastructure_failed',
                'comparison_verdict':'not-comparable','details':{'reason':'missing workload endpoint'}}
    try:
        data=json.loads(path.read_text())
        require(data['execution_status'] in ('succeeded','failed','infrastructure_failed','rejected'),'invalid execution result')
        require(data['comparison_verdict'] in ('not-run','equal','different','inconclusive','not-comparable'),'invalid verdict')
        require(data['template_id']==job['template_id'],'endpoint template mismatch')
        if returncode!=0 and data['execution_status'] != 'rejected':
            data['execution_status']='failed'
        return {key:data[key] for key in ('execution_status','comparison_verdict','details')}
    except (ValueError,KeyError,TypeError):
        return {'execution_status':'infrastructure_failed','comparison_verdict':'not-comparable','details':{'reason':'invalid workload endpoint'}}

def build_profile(profile,config,repo_root,campaign_id,*,research_state_root=None):
    repo=Path(repo_root).resolve()
    if research_state_root is None:
        ensure_released_profile(profile)
    if profile in RESEARCH_CANDIDATES:
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
        admission_module().clean_source(repo, revision)
        inputs = [(_path(config, 'retained_capture')/'image.bin', 12000000),
                  (_path(config, 'retained_capture')/'heap.bin', 120000000)] if profile == 'research-anomalies' else [
                      (_path(config, 'original_executable'), 7192576)]
        for path, ceiling in inputs:
            require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= ceiling,
                    'unsupported research input object or size')
        if profile == 'research-consumers':
            require(inputs[0][0].stat().st_size == 7192576, 'unapproved specimen size')
            capstone_version = subprocess.check_output([str(_path(config, 'oracle_python')), '-I', '-c',
                                                        'import capstone; print(capstone.__version__)'], text=True).strip()
            require(capstone_version == '5.0.7', 'qualified disassembler version must be 5.0.7')
        python_version = subprocess.check_output([str(_path(config, 'python')), '--version'], text=True).strip()
        require(python_version.startswith('Python 3.12.'), 'qualified Python 3.12 required')
    choices={'synthetic':['synthetic-progress-v1'],
             'regression':['rng-native-wasm-v1','original-r10-regression-v1','bosman-same-save-v1'],
             'research-squad':['research-squad-members-v1'],
             **{name: [item['template']] for name, item in RESEARCH_CANDIDATES.items()}}
    require(profile in choices,'unknown approved profile')
    jobs=[]
    for index,template in enumerate(choices[profile]):
        paths=sorted(set(_files(template,config,repo)))
        jobs.append({'job_id':f'{index+1:03d}-{template}','template_id':template,'parameters':({'steps':100,'delay_ms':100,'mode':'normal'} if template=='synthetic-progress-v1' else {}),
                     'pins':[{'path':str(p),'sha256':sha(p)} for p in paths]})
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    global_paths=[repo/'tools/lab'/name for name in ('core.py','workloads.py','admission.py','lab.py','report.py','hold.py','Hold-Lab.ps1','Lab.ps1','Lab.cmd')]
    worktree=subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=repo,text=True)
    diff=subprocess.check_output(['/usr/bin/git','diff','--binary','HEAD'],cwd=repo)
    versions={'git':subprocess.check_output(['/usr/bin/git','--version'],text=True).strip()}
    for key in ('python','node','oracle_python'):
        if key=='python' or key in config:
            versions[key]=subprocess.check_output([str(_path(config,key)),'--version'],text=True,stderr=subprocess.STDOUT).strip()
    manifest = {'schema_version':1,'campaign_id':campaign_id,'profile_id':profile,'source_revision':revision,
            'pins':[{'path':str(p),'sha256':sha(p)} for p in global_paths if p.is_file()],'jobs':jobs,
            'limits':{'max_jobs':len(jobs),'elapsed_seconds':1800,'stall_seconds':660,
                      'output_bytes':2*1024**2,'disk_bytes':512*1024**2,'min_free_bytes':1024**3,'max_attempts':2},
            'stop_conditions':{'max_failures':1,'stop_on_divergence':True},
            'provenance':{'config_sha256':_config_digest(config),'source_dirty':bool(worktree),
                          'source_worktree_status':worktree,'source_diff_sha256':hashlib.sha256(diff).hexdigest(),
                          'tool_versions':versions,'scope':'approved templates; no automatic evidence promotion',
                          'research_protocol':'docs/research/LOCAL_LAB_RESEARCH_V1.md' if profile=='research-squad' else None}}
    if profile in RESEARCH_CANDIDATES:
        admission = admission_module()
        admission.clean_source(repo, revision)
        manifest['limits'] = dict(admission.LIMITS)
        manifest['observation_seconds'] = 0
        manifest['provenance']['research_protocol'] = RESEARCH_CANDIDATES[profile]['protocol']
        manifest['provenance']['research_state_root'] = str(Path(research_state_root).resolve())
        if profile == 'research-consumers':
            manifest['provenance']['tool_versions']['capstone'] = capstone_version
        admission.validate_shape(manifest)
        # Freeze reads and hashes private files, but never invokes the decoder.
        if profile == 'research-anomalies':
            capture = _path(config, 'retained_capture')
            require(sha(capture/'image.bin') == IMAGE_SHA and sha(capture/'heap.bin') == HEAP_SHA,
                    'unapproved retained capture')
        else:
            require(sha(_path(config,'original_executable')) == SPECIMEN_SHA, 'unapproved original specimen')
    return manifest


def reserve_attempt(manifest, attempt):
    if is_research(manifest):
        return admission_module().reservation(manifest, attempt=attempt)

def _progress(attempt,sequence):
    temp=attempt/'progress.tmp'
    temp.write_text(json.dumps({'sequence':sequence}))
    temp.replace(attempt/'progress.json')

def _run(command,attempt,name,require_success=True):
    with (attempt/(name+'.stdout')).open('xb') as out,(attempt/(name+'.stderr')).open('xb') as err:
        code=subprocess.call(command,stdout=out,stderr=err)
    if require_success:
        require(code==0,name+' failed')
    return code

def _research(config):
    """Independent read-only all-slot structural question. Raw records stay private."""
    capture=_path(config,'retained_capture')
    image,heap=(capture/'image.bin').read_bytes(),(capture/'heap.bin').read_bytes()
    require(hashlib.sha256(image).hexdigest()==IMAGE_SHA and hashlib.sha256(heap).hexdigest()==HEAP_SHA,'capture identity')
    def read(address,size):
        for base,raw in ((0x400000,image),(0x70000000,heap)):
            if base<=address and address+size<=base+len(raw):
                return raw[address-base:address-base+size]
        raise ValueError('missing captured extent')
    def u32(address):
        return struct.unpack('<I',read(address,4))[0]
    clubs,nations,staff,players=[u32(a) for a in (0xae235c,0xae2350,0xae2364,0xae236c)]
    cb,sb,pb=[u32(a) for a in (0xae23b4,0xae23bc,0xae23c4)]
    require(0<2*nations<clubs<=10000 and 16<staff<=100000 and 0<players<=100000,'dimensions')
    table=read(pb,players*70)
    require(all(struct.unpack_from('<I',table,i*70)[0]==i for i in range(players)),'player table IDs')
    bindings=[]
    for index in range(clubs-2*nations):
        club=cb+index*581
        manager=u32(club+0xcf)
        if sb<=manager<sb+staff*110 and (manager-sb)%110==0 and (manager-sb)//110>=staff-16:
            require(u32(club)==index and u32(manager)==(manager-sb)//110 and u32(manager+0x39)==club,'human binding')
            bindings.append(club)
    require(len(bindings)==1,'unique human binding')
    club=bindings[0]
    counts=dict(slots=50,invalid_staff=0,foreign_club=0,reciprocal_staff=0,complete_player_id=0,
                unaligned_player=0,missing_player_extent=0,wrong_player_id=0,duplicate_staff=0,duplicate_player=0)
    seen_staff,seen_player,hashes=set(),set(),[]
    list_candidates=set()
    list_values=[]
    def player_identity(pointer,data=None):
        require(pb<=pointer<pb+players*70 and (pointer-pb)%70==0,'unaligned player')
        raw=read(pointer,70) if data is None else data
        require(len(raw)==70,'player extent')
        require(struct.unpack_from('<I',raw)[0]==(pointer-pb)//70,'player ID')
        return raw
    first=None
    for slot in range(50):
        ptr=u32(club+0xd7+slot*4)
        if not(sb<=ptr<sb+staff*110 and (ptr-sb)%110==0):
            counts['invalid_staff']+=1
            continue
        require(u32(ptr)==(ptr-sb)//110,'staff ID')
        counts['duplicate_staff']+=ptr in seen_staff
        seen_staff.add(ptr)
        if u32(ptr+0x39)!=club:
            counts['foreign_club']+=1
            continue
        counts['reciprocal_staff']+=1
        player=u32(ptr+0x61)
        if not(pb<=player<pb+players*70 and (player-pb)%70==0):
            counts['unaligned_player']+=1
            continue
        try:
            raw=read(player,70)
        except ValueError:
            counts['missing_player_extent']+=1
            continue
        if struct.unpack_from('<I',raw)[0]!=(player-pb)//70:
            counts['wrong_player_id']+=1
            continue
        counts['complete_player_id']+=1
        list_candidates.add(ptr)
        list_values.append(ptr)
        counts['duplicate_player']+=player in seen_player
        seen_player.add(player)
        first=first or (player,raw)
        hashes.append({'staff_sha256':hashlib.sha256(read(ptr,110)).hexdigest(),
                       'player_sha256':hashlib.sha256(raw).hexdigest()})
    controls={}
    if first:
        ptr,raw=first
        bad=struct.pack('<I',((ptr-pb)//70+1)&0xffffffff)+raw[4:]
        for name,args in [('unaligned-link',(ptr+1,None)),('wrong-player-id',(ptr,bad)),('short-player-record',(ptr,raw[:-1]))]:
            try:
                player_identity(*args)
            except ValueError:
                controls[name]=True
            else:
                controls[name]=False
    # Novel completeness question: independently invert the entire known staff
    # table club pointer, retaining every excluded association in the denominator.
    inverse=set()
    associations=dict(total=0,complete_player=0,invalid_player=0)
    first_staff=None
    def club_association(raw):
        return struct.unpack_from('<I',raw,0x39)[0]==club
    for index in range(staff):
        pointer=sb+index*110
        raw=read(pointer,110)
        require(struct.unpack_from('<I',raw)[0]==index,'complete staff table IDs')
        if not club_association(raw):
            continue
        associations['total']+=1
        link=struct.unpack_from('<I',raw,0x61)[0]
        try:
            player_identity(link)
        except ValueError:
            associations['invalid_player']+=1
            continue
        associations['complete_player']+=1
        inverse.add(pointer)
        first_staff=first_staff or (pointer,raw)
    def complete_list(values,expected):
        return len(values)==len(set(values)) and set(values)==expected
    baseline=sorted(list_candidates)
    # Controls are evaluated against a known complete artificial identity set,
    # rather than assuming the scientific equality hypothesis is true.
    if baseline:
        controls['missing-member']=not complete_list(baseline[:-1],set(baseline))
        controls['duplicate-member']=not complete_list(baseline+[baseline[0]],set(baseline))
    if first_staff:
        pointer,raw=first_staff
        changed=raw[:0x39]+struct.pack('<I',0)+raw[0x3d:]
        controls['changed-club-backpointer']=not club_association(changed)
    def identity_set(values):
        return hashlib.sha256(canonical([hashlib.sha256(read(p,110)).hexdigest() for p in sorted(values)])).hexdigest()
    return {'question_id':'r10-inverse-club-candidate-completeness-v1','counts':counts,
            'inverse_associations':associations,
            'set_comparison':{'list_distinct':len(list_candidates),'inverse_distinct':len(inverse),
                'intersection':len(list_candidates & inverse),'list_only':len(list_candidates-inverse),
                'inverse_only':len(inverse-list_candidates),'list_identity_sha256':identity_set(list_candidates),
                'inverse_identity_sha256':identity_set(inverse)},
            'hypotheses':{'H1_exact_candidate_set_equality':complete_list(list_values,inverse)},
            'known_regression':{'reciprocal_complete_43':counts['reciprocal_staff']==43 and counts['complete_player_id']==43,
                                'anomalies_2_and_5':counts['invalid_staff']==2 and counts['foreign_club']==5},
            'controls':controls,'record_identity_sha256':hashlib.sha256(canonical(hashes)).hexdigest(),
            'player_table_sha256':hashlib.sha256(table).hexdigest(),'production_admission':'none',
            'scope':'captured structural identity and inverse association only; squad eligibility/lifetime unknown'}

def _execute(task):
    attempt,repo,config=Path(task['attempt_dir']),Path(task['repo_root']),task['config']
    template,params=task['template_id'],task['parameters']
    outcome={'template_id':template,'execution_status':'failed','comparison_verdict':'not-comparable','details':{}}
    try:
        validate(task['manifest'],repo,config)
        validate_job(task['manifest'],task['job'],repo,config)
        _progress(attempt,0)
        if template=='synthetic-progress-v1':
            mode=params.get('mode','normal')
            if mode=='stall':
                time.sleep(3600)
            if mode=='child-orphan':
                subprocess.Popen([str(_path(config,'python')),'-I','-c','import time; time.sleep(3600)'])
                time.sleep(3600)
            if mode=='output':
                while True:
                    os.write(1,b'x'*8192)
            for index in range(params.get('steps',3)):
                time.sleep(params.get('delay_ms',10)/1000)
                _progress(attempt,index+1)
            require(mode!='fail','injected failure')
            outcome.update(execution_status='succeeded',comparison_verdict='not-run',details={'synthetic':True,'steps':params.get('steps',3)})
        elif template=='rng-native-wasm-v1':
            _run([str(_path(config,'rng_native'))],attempt,'native')
            _progress(attempt,1)
            _run([str(_path(config,'node')),str(repo/'scripts/r1/run_wasm.mjs'),str(_path(config,'rng_wasm')),str(attempt/'wasm.bin')],attempt,'wasm')
            native,wasm=(attempt/'native.stdout').read_bytes(),(attempt/'wasm.bin').read_bytes()
            controls=struct.unpack('<4I',native[-16:]) if len(native)==75952 else (0,0,0,0)
            equal=native==wasm and hashlib.sha256(native).hexdigest()==RNG_SHA and all(controls)
            outcome.update(execution_status='succeeded',comparison_verdict='equal' if equal else 'different',
                           details={'native_sha256':hashlib.sha256(native).hexdigest(),'wasm_sha256':hashlib.sha256(wasm).hexdigest(),
                                    'canonical_bytes':len(native),'negative_control_mismatches':list(controls),'regression':True})
        elif template=='original-r10-regression-v1':
            _run([str(_path(config,'oracle_python')),str(repo/'scripts/qualify_pc_r10_command.py'),
                  str(_path(config,'original_executable')),str(_path(config,'retained_capture')),str(attempt/'oracle.json')],attempt,'oracle')
            receipt=json.loads((attempt/'oracle.json').read_text())
            equal=sha(attempt/'oracle.json')==sha(repo/'docs/research/evidence/pc-r10-command-retained-oracle-v1.json') and receipt.get('successful_calls')==11 and receipt.get('censored_calls')==4 and receipt.get('checkpoint_continuation')=='exact' and len(receipt.get('defect_controls',{}))==12 and all(receipt['defect_controls'].values())
            outcome.update(execution_status='succeeded',comparison_verdict='equal' if equal else 'different',
                           details={'successful_calls':receipt.get('successful_calls'),'censored_calls':receipt.get('censored_calls'),
                                    'controls':receipt.get('defect_controls'),'regression':True,'production_admission':'none'})
        elif template=='bosman-same-save-v1':
            request=json.loads(_path(config,'bosman_request').read_text())
            request['attempt_id']='lab-'+task['job_id']
            request['backend']['expected_executable_sha256']=sha(_path(config,'bosman_adapter'))
            request['backend']['source_revision']=task['manifest']['source_revision']
            (attempt/'bosman-request.json').write_text(json.dumps(request))
            _run([str(_path(config,'bosman_supervisor')),'execute-process','--request',str(attempt/'bosman-request.json'),
                  '--backend-executable',str(_path(config,'bosman_adapter')),'--backend-config',str(_path(config,'bosman_config')),
                  '--attempt-dir',str(attempt/'bosman')],attempt,'bosman')
            receipt=json.loads((attempt/'bosman/replay-manifest.json').read_text())
            require(receipt.get('execution',{}).get('status')=='succeeded' and
                    receipt['execution'].get('stop_condition')=='classic-same-save-normal-again-14-days-equal',
                    'Bosman endpoint missing')
            outcome.update(execution_status='succeeded',comparison_verdict='not-run',
                           details={'regression':True,'endpoint':'classic-same-save-normal-again-14-days-equal',
                                    'comparison_scope':'internal same-save assertion; no original-process comparison'})
        elif template=='research-squad-members-v1':
            observations=_research(config)
            (attempt/'research-observations.json').write_text(json.dumps(observations,indent=2)+'\n')
            require(len(observations['controls'])==6 and all(observations['controls'].values()),'research controls did not discriminate')
            outcome.update(execution_status='succeeded',comparison_verdict='not-run',details=observations)
        elif template in ('research-squad-anomalies-v1', 'research-member-consumers-v1'):
            # validate_job above requires immutable operational/qualification receipts.
            number = '005' if template == 'research-squad-anomalies-v1' else '006'
            interpreter = 'python' if number == '005' else 'oracle_python'
            input_key = 'retained_capture' if number == '005' else 'original_executable'
            code = _run([str(_path(config, interpreter)), '-I', str(repo/f'scripts/lab{number}.py'),
                        str(_path(config, input_key)), str(attempt)], attempt, 'research', require_success=False)
            endpoint = json.loads((attempt/f'lab{number}-result.json').read_text())
            require(endpoint['execution_status'] in ('succeeded', 'failed', 'rejected'), 'invalid research status')
            require(endpoint['comparison_verdict'] in ('equal', 'different', 'inconclusive', 'not-run', 'not-comparable'),
                    'invalid research comparison')
            require(code == 0 or endpoint['execution_status'] != 'succeeded', 'research process failed with successful endpoint')
            outcome.update({key: endpoint[key] for key in ('execution_status', 'comparison_verdict', 'details')})
        validate(task['manifest'],repo,config)
        validate_job(task['manifest'],task['job'],repo,config)
        _progress(attempt,1000000)
    except Exception as error:
        outcome['details']={'error_type':type(error).__name__,'reason':str(error)[:500]}
    (attempt/'workload-result.json').write_text(json.dumps(outcome,indent=2)+'\n')
    return 0 if outcome['execution_status']=='succeeded' else 1

if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='_execute':
        raise SystemExit('internal approved workload entry point')
    raise SystemExit(_execute(json.loads(Path(sys.argv[2]).read_text())))

