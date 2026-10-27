"""Invented-instruction/temporary-state controls only. Never opens retained data."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capstone
import unicorn
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EFLAGS, UC_X86_REG_XMM0, UC_X86_REG_EIP
import lab007 as lab


def invented(code):
    oracle = lab.MatrixOracle.__new__(lab.MatrixOracle)
    oracle.uc = uc = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
    for start, length in ((0x1000, 4096), (0x2000, 4096), (lab.STACK, 65536), (lab.STOP, 4096)):
        uc.mem_map(start, length)
    uc.mem_write(0x1000, code)
    oracle.decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    oracle.decoder.detail = True
    oracle.instruction_sizes = {i.address: i.size for i in oracle.decoder.disasm(code, 0x1000)}
    oracle.events, oracle.current_starts, oracle.ordered_reads, oracle.write_pcs = [], [], [], []
    oracle.starts, oracle.reads, oracle.calls = set(), set(), []
    oracle.writes, oracle.allowed_writes, oracle.fields, oracle.ids = [], [], {}, [1, 2]
    oracle.target, oracle.pc, oracle.decoded, oracle.boundary, oracle.trace_stream = 0x2000, 0x1000, None, None, None
    for kind, method in ((unicorn.UC_HOOK_CODE, oracle.instruction), (unicorn.UC_HOOK_MEM_READ, oracle.read),
                         (unicorn.UC_HOOK_MEM_WRITE, oracle.write), (unicorn.UC_HOOK_MEM_INVALID, oracle.invalid)):
        uc.hook_add(kind, method)
    return oracle


class CompleteEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.oracle = invented(bytes.fromhex('4090'))
        self.state = lab.CompleteState(self.oracle.uc, self.root)

    def test_all_mappings_padding_cpu_and_lossless_delta(self):
        uc = self.oracle.uc
        uc.mem_write(0x1fff, b'X')  # image alignment padding
        uc.mem_write(0x2fff, b'Y')  # heap alignment padding
        uc.mem_write(lab.STOP+4095, b'Z')
        uc.reg_write(UC_X86_REG_EAX, 91)
        uc.reg_write(UC_X86_REG_EFLAGS, 0x202)
        uc.reg_write(UC_X86_REG_XMM0, 123456789)
        observed = self.state.save('changed')
        reconstructed = lab.reconstruct(self.root, self.state.description, observed)
        self.assertEqual(reconstructed, [bytes(uc.mem_read(a, b-a+1)) for a, b, _ in self.state.regions])
        with self.assertRaisesRegex(ValueError, 'untouched'):
            self.state.unchanged_except(0x2000, None)
        self.state.reset()
        self.assertEqual(bytes(self.state.evidence_cpu), self.state.raw_cpu)
        self.assertEqual([bytes(uc.mem_read(a, len(raw))) for (a, _, _), raw in
                          zip(self.state.regions, self.state.base)], self.state.base)

    def test_cpu_payload_mutation_and_exact_normalization(self):
        raw = self.state.raw_cpu
        identity = lab.cpu_identity(raw)
        for offset in (40, 100, len(raw)-1):
            changed = bytearray(raw); changed[offset] ^= 1
            self.assertNotEqual(lab.cpu_identity(changed), identity)
        for offset in range(20, 32):
            changed = bytearray(raw); changed[offset] ^= 1
            self.assertEqual(lab.cpu_identity(changed), identity)
        for offset in (0, 8, 12, 16, 32):
            changed = bytearray(raw); changed[offset] ^= 1
            with self.assertRaises(ValueError): lab.cpu_identity(changed)

    def test_cpu_and_mapped_state_are_deterministic_across_fresh_processes(self):
        command = [sys.executable, '-B', '-I', str(Path(__file__).resolve()), '--cpu-fixture']
        results = [subprocess.check_output(command) for _ in range(3)]
        self.assertEqual(results, [results[0]]*3)
        facts = json.loads(results[0])
        self.assertNotEqual(facts['before']['cpu'], facts['after']['cpu'])

    def test_changed_mapping_permissions_or_extra_region_reject(self):
        uc = self.oracle.uc
        uc.mem_protect(0x2000, 4096, unicorn.UC_PROT_READ)
        with self.assertRaisesRegex(ValueError, 'mapping changed'): self.state.reset()
        uc.mem_protect(0x2000, 4096, unicorn.UC_PROT_ALL)
        uc.mem_map(0x3000, 4096)
        with self.assertRaisesRegex(ValueError, 'mapping changed'): self.state.save('bad')

    def test_malformed_delta_omission_duplicate_order_or_bytes_reject(self):
        self.oracle.uc.mem_write(0x1001, b'X')
        self.oracle.uc.mem_write(0x2001, b'Y')
        state = self.state.save('delta')
        for mutate in (lambda x: x['regions'][0].update(pages=[]),
                       lambda x: x['regions'][0]['pages'].append(x['regions'][0]['pages'][0]),
                       lambda x: x['regions'][1]['pages'][0].update(data_offset=0),
                       lambda x: x['regions'][0]['pages'][0].update(offset=1),
                       lambda x: x['regions'].pop()):
            changed = copy.deepcopy(state); mutate(changed)
            with self.assertRaises(ValueError): lab.reconstruct(self.root, self.state.description, changed)

    def test_reset_corruption_is_detected(self):
        original = self.oracle.uc.context_restore
        def broken(context):
            original(context)
            self.oracle.uc.reg_write(UC_X86_REG_XMM0, 7)
        with patch.object(self.oracle.uc, 'context_restore', broken):
            with self.assertRaisesRegex(ValueError, 'CPU reset'): self.state.reset()


class BoundaryTests(unittest.TestCase):
    def test_forbidden_instruction_and_call_before_effects(self):
        for code in (bytes.fromhex('4090'), bytes.fromhex('40e8fa0f0000')):
            oracle = invented(code)
            if code[-1] == 0x90: del oracle.instruction_sizes[0x1001]
            with self.assertRaises(lab.Boundary): oracle.uc.emu_start(0x1000, 0x1000+len(code))
            self.assertEqual(oracle.uc.reg_read(UC_X86_REG_EAX), 1)
            self.assertEqual(oracle.uc.reg_read(UC_X86_REG_EIP), 0x1001)

    def test_forbidden_read_write_stop_before_effect_and_retain_prior(self):
        for code in ('40a100200000', '40c7050020000007000000'):
            oracle = invented(bytes.fromhex(code))
            oracle.uc.mem_write(0x2000, bytes.fromhex('99000000'))
            with self.assertRaises(lab.Boundary): oracle.uc.emu_start(0x1000, 0x1000+len(bytes.fromhex(code)))
            self.assertEqual(oracle.uc.reg_read(UC_X86_REG_EAX), 1)
            self.assertEqual(bytes(oracle.uc.mem_read(0x2000, 4)), bytes.fromhex('99000000'))
            self.assertEqual(oracle.uc.reg_read(UC_X86_REG_EIP), 0x1001)

    def test_invalid_initial_fetch_is_censored(self):
        oracle = invented(b'\x90')
        oracle.pc = None
        oracle.before_entry = lambda: None
        with self.assertRaises(lab.Boundary): oracle.call(0x3000, [], 0)
        self.assertEqual(oracle.boundary['pc'], '00003000')
        self.assertEqual(oracle.boundary['kind'], 'memory')

    def test_entry_snapshot_after_abi_setup_and_complete_return_facts(self):
        oracle = invented(bytes.fromhex('b801000000c3'))
        with tempfile.TemporaryDirectory() as directory:
            complete = lab.CompleteState(oracle.uc, directory)
            observed = []
            oracle.before_entry = lambda: observed.append(complete.save('entry'))
            returned, abi = oracle.call(0x1000, [], 42, [], 1)
            self.assertEqual(returned, 1)
            self.assertEqual(abi['actual_pc'], lab.STOP)
            self.assertEqual(abi['actual_saved'], abi['expected_saved'])
            self.assertNotEqual(observed[0]['cpu'], complete.description['cpu'])
            raw = lab.reconstruct(directory, complete.description, observed[0])
            stack_index = next(i for i, r in enumerate(complete.regions) if r[0] == lab.STACK)
            self.assertEqual(int.from_bytes(raw[stack_index][0x8000:0x8004], 'little'), lab.STOP)

    def test_300_instruction_path_with_durable_memory_trace_within_call_limit(self):
        oracle = invented(bytes.fromhex('a10020000040')*150+bytes.fromhex('c3'))
        oracle.fields = {'invented': (0x2000, 4)}
        oracle.before_entry = lambda: None
        with tempfile.TemporaryDirectory() as directory:
            with (Path(directory)/'trace').open('wb') as stream:
                oracle.trace_stream = stream
                started = time.monotonic()
                value, _ = oracle.call(0x1000, [], 0, [], 1)
                oracle.flush_trace()
                elapsed = time.monotonic()-started
            self.assertEqual(value, 1)
            self.assertEqual(len(oracle.current_starts), 301)
            self.assertLess(elapsed, lab.CALL_TIMEOUT_MICROSECONDS/1_000_000)
            print(f'Invented 301-instruction fsynced trace: {elapsed:.6f}s', file=sys.stderr)

    def test_instruction_or_timeout_limit_censors_and_keeps_partial_effect(self):
        for deadline in (lab.CALL_TIMEOUT_MICROSECONDS, 1):
            oracle = invented(bytes.fromhex('40ebfd'))
            oracle.before_entry = lambda: None
            with patch.object(lab, 'CALL_TIMEOUT_MICROSECONDS', deadline), self.assertRaises(lab.Boundary):
                oracle.call(0x1000, [], 0)
            self.assertEqual(oracle.boundary['kind'], 'execution-limit')
            self.assertLessEqual(len(oracle.current_starts), 3000)
            if deadline == lab.CALL_TIMEOUT_MICROSECONDS:
                self.assertGreater(oracle.uc.reg_read(UC_X86_REG_EAX), 0)
                self.assertEqual(len(oracle.current_starts), 3000)


class FrozenAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1]/'tools/lab/lab007_admission.py'
        spec = importlib.util.spec_from_file_location('test_lab007_admission', path)
        cls.admission = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.admission)

    def manifest(self):
        a = self.admission
        m = {'campaign_id': 'fixture', 'profile_id': a.PROFILE, 'observation_seconds': 0,
             'jobs': [{'pins': []}], 'limits': dict(a.LIMITS),
             'stop_conditions': {'max_failures': 1, 'stop_on_divergence': True},
             'provenance': {'source_dirty': False, 'case_list_sha256': a.CASE_SHA,
                            'selected_replay_job': a.SELECTED_JOB}}
        m['jobs'] = a.original_jobs(m)
        return m

    def test_exact_matrix_and_only_selected_replay(self):
        a, m = self.admission, self.manifest()
        a.validate_shape(m)
        original = a.subject(m)
        m['jobs'] = [m['jobs'][-1]]
        m['provenance']['replay_of'] = {'job_id': a.SELECTED_JOB}
        a.validate_shape(m)
        self.assertEqual(a.subject(m), original)
        m['jobs'][0]['job_id'] = '011-retained-assignment'
        with self.assertRaises(ValueError): a.validate_shape(m)

    def test_case_grouping_and_cardinality(self):
        rows = self.admission.cases(Path(__file__).resolve().parents[1])
        self.assertEqual([len(x['cases']) for x in rows], [10]*12)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'docs/research'; path.mkdir(parents=True)
            changed = {'jobs': copy.deepcopy(rows)}
            changed['jobs'][0]['cases'].append(changed['jobs'][1]['cases'].pop(0))
            (path/'LAB_007_CASES_V1.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'grouping'): self.admission.cases(directory)

    def test_incomplete_or_changed_precursor_not_accepted(self):
        with self.assertRaises(ValueError): self.admission.precursor({'sha256': '0'*64})

    def test_real_core_selected_replay_constructor_and_review_binding(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools/lab'))
        import core
        a, manifest = self.admission, self.manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = Path(__file__).resolve().parents[1]
            revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
            manifest.update(schema_version=1, source_revision=revision, pins=[a.reference(Path(core.__file__))])
            manifest['provenance']['research_state_root'] = str(root)
            review = {'schema_version': 1, 'kind': 'research-operational-review-v1',
                      'decision': 'approved-for-pilot', 'reviewer': 'invented reviewer',
                      'implementation_author': 'invented author', 'source_revision': revision,
                      'campaign_id': 'fixture', 'frozen_subject_sha256': a.subject(manifest)}
            path = root/'review.json'; path.write_bytes(a.canonical(review))
            manifest['provenance']['pilot_admission'] = {'operational_review': a.reference(path),
                                                        'qualification_acceptance': {}, 'precursor_acceptance': {}}
            adapter = types.SimpleNamespace(validate=lambda m, repo, config=None: a.validate(m, repo),
                                            validate_job=lambda *args, **kwargs: None)
            with patch.object(a.base, 'qualification'), patch.object(a, 'precursor'), \
                    patch.object(a.base, 'clean_source'), patch.object(a, 'reservation'):
                core.configure(root, repo, manifest, adapter)
                replay_id = core.replay(root, repo, 'fixture', a.SELECTED_JOB, adapter)
                result = core.snapshot(root, replay_id)['campaign']['manifest']
                self.assertEqual(result['jobs'], [manifest['jobs'][-1]])
                self.assertEqual(result['limits'], manifest['limits'])
                self.assertEqual(a.subject(result), a.subject(manifest))
                with self.assertRaises(ValueError): core.replay(root, repo, 'fixture', '001-retained-assignment', adapter)
                changed = copy.deepcopy(manifest); changed['provenance']['extra'] = True
                with self.assertRaisesRegex(ValueError, 'subject changed'): a.validate(changed, repo)

    def test_all_26_physical_allocations_and_second_replay_fence(self):
        a, manifest = self.admission, self.manifest()
        with tempfile.TemporaryDirectory() as directory, patch.object(a.base, 'TOTAL_RESERVE', 27*4096), \
                patch.object(a.base, 'ATTEMPT_RESERVE', 4096):
            root = Path(directory)
            manifest['provenance']['research_state_root'] = str(root)
            allocation = a.reservation(manifest, create=True)
            self.assertGreaterEqual(Path(allocation['path']).stat().st_blocks*512, 27*4096)
            serial = 0
            for job in manifest['jobs']:
                for ordinal in (1, 2):
                    serial += 1
                    attempt = {'attempt_id': str(serial), 'campaign_id': 'fixture', 'job_id': job['job_id'],
                               'ordinal': ordinal, 'directory': str(root/'attempts'/str(serial))}
                    a.reservation(manifest, attempt=attempt)
                    self.assertEqual(a.reservation(manifest, attempt=attempt)['consumed_attempts'], serial)
            replay = copy.deepcopy(manifest)
            replay['jobs'] = [replay['jobs'][-1]]
            replay['provenance']['replay_of'] = {'job_id': a.SELECTED_JOB}
            for ordinal in (1, 2):
                serial += 1
                attempt.update(attempt_id=str(serial), campaign_id='replay', ordinal=ordinal,
                               directory=str(root/'attempts'/str(serial)))
                a.reservation(replay, attempt=attempt)
            self.assertEqual(Path(allocation['path']).stat().st_size, 4096)
            attempt.update(attempt_id='duplicate', directory=str(root/'attempts/duplicate'))
            with self.assertRaisesRegex(ValueError, 'duplicate job attempt ordinal'):
                a.reservation(replay, attempt=attempt)
            attempt.update(campaign_id='replay-two')
            with self.assertRaisesRegex(ValueError, 'one pilot and one replay'):
                a.reservation(replay, attempt=attempt)


class InterruptedAccountingTests(unittest.TestCase):
    def test_initial_denominator_survives_input_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(lab, 'checked', side_effect=ValueError('invented failure')):
            self.assertEqual(lab.execute('never-read', 'never-read', directory, '012-retained-assignment'), 1)
            evidence = json.loads((Path(directory)/'lab007-checkpoint.json').read_text())
            self.assertEqual(len(evidence['cases']), 10)
            self.assertEqual(sum(len(c['calls']) for c in evidence['cases']), 27)
            self.assertTrue(all(c['status'] == 'unstarted' for c in evidence['cases']))

    def test_durable_trace_survives_censored_instruction(self):
        with tempfile.TemporaryDirectory() as directory:
            oracle = invented(bytes.fromhex('40a100200000'))
            path = Path(directory)/'trace'
            with path.open('wb') as stream:
                oracle.trace_stream = stream
                with self.assertRaises(lab.Boundary): oracle.uc.emu_start(0x1000, 0x1006)
            events = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(events[-1]['kind'], 'denied-read')
            self.assertEqual(events[0]['address'], 0x1000)
            receipt = json.loads(Path(str(path)+'.durable.json').read_text())
            self.assertEqual(receipt['durable_through_sequence'], len(events))
            self.assertEqual(receipt['prefix_sha256'], lab.digest(path.read_bytes()))


if __name__ == '__main__':
    if sys.argv[1:] == ['--cpu-fixture']:
        with tempfile.TemporaryDirectory() as directory:
            oracle = invented(bytes.fromhex('4090'))
            state = lab.CompleteState(oracle.uc, directory)
            before = state.save('before')
            oracle.uc.emu_start(0x1000, 0x1002)
            after = state.save('after')
            state.reset()
            print(lab.canonical({'before': lab.scientific(before), 'after': lab.scientific(after)}).decode())
    else:
        unittest.main()
