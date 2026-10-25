"""Lightweight admission/report controls; never acquire the live heavy slot."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w = load('candidate_workloads', ROOT/'tools/lab/workloads.py')
cases = load('candidate_cases', ROOT/'scripts/lab007_cases.py')


class CandidateAdmission(unittest.TestCase):
    def test_no_private_input_access_before_release_gate(self):
        with patch.object(w, '_files', side_effect=AssertionError('private input accessed')):
            for profile, candidate in w.RESEARCH_CANDIDATES.items():
                with self.subTest(profile=profile):
                    with self.assertRaisesRegex(ValueError, 'Research release blocked'):
                        w.build_profile(profile, {}, ROOT, 'blocked')
                    with self.assertRaisesRegex(ValueError, 'Research release blocked'):
                        w.validate_job({}, {'template_id': candidate['template'], 'parameters': {}}, ROOT, {})

    def test_cannot_bypass_gate_with_parameters_or_claimed_approval(self):
        for candidate in w.RESEARCH_CANDIDATES.values():
            job = {'template_id': candidate['template'], 'parameters': {'approved': True}}
            with self.assertRaisesRegex(ValueError, 'Research release blocked'):
                w.validate_job({'approved': True}, job, ROOT, {'approved': True})
        with self.assertRaisesRegex(ValueError, 'unapproved template'):
            w.validate_job({}, {'template_id': 'research-assignment-matrix-v1'}, ROOT, {})

    def test_cli_rejects_before_service_or_private_config_access(self):
        import lab
        for profile in w.RESEARCH_CANDIDATES:
            with patch.object(sys, 'argv', ['lab.py', 'start', profile]), \
                    patch.object(lab, 'service_active') as service, \
                    patch.object(Path, 'read_text') as read:
                with self.assertRaisesRegex(ValueError, 'Research release blocked'):
                    lab.main()
                service.assert_not_called()
                read.assert_not_called()

    def test_complete_case_definition_is_immutable_and_not_executable(self):
        frozen = json.loads((ROOT/'docs/research/LAB_007_CASES_V1.json').read_text())
        self.assertEqual(frozen, cases.definition())
        self.assertFalse(frozen['execution_approved'])
        self.assertEqual(len(frozen['jobs']), 12)
        self.assertTrue(all(len(job['cases']) == 10 for job in frozen['jobs']))
        rows = [case for job in frozen['jobs'] for case in job['cases']]
        self.assertEqual(len({row['case_id'] for row in rows}), 120)
        self.assertEqual({(r['slot'], r['first_member'], r['sequence']) for r in rows},
                         {(s, m, q) for s in range(20) for m in range(2)
                          for q in ('assign-read', 'repeat-read', 'replace-read')})
        raw = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), frozen['case_list_sha256'])
        for row in rows:
            first = row['first_member']
            expected = {'assign-read': [first], 'repeat-read': [first, first],
                        'replace-read': [first, 1-first]}[row['sequence']]
            self.assertEqual(row['assignments'], expected)

    def test_readiness_reports_all_unstarted_and_no_acceptance(self):
        rows = w.research_readiness(ROOT)
        self.assertEqual([r['campaign'] for r in rows], ['LAB-005', 'LAB-006', 'LAB-007'])
        for row in rows:
            self.assertFalse(row['execution_approved'])
            self.assertFalse(row['executed'])
            self.assertFalse(row['independently_accepted'])
        self.assertEqual(rows[-1]['unstarted_cases'], 120)

    def test_readiness_cli_needs_no_service_or_private_configuration(self):
        result = subprocess.run([sys.executable, str(ROOT/'tools/lab/lab.py'),
                                 '--root', '/nonexistent/research-unit', 'readiness'],
                                check=True, text=True, capture_output=True)
        self.assertEqual(len(json.loads(result.stdout)), 3)
        self.assertEqual(result.stderr, '')

    def test_private_report_preserves_rejected_and_unstarted_jobs(self):
        # Render only: no worker, database or execution lock is started.
        from report import write_report
        manifest = {'source_revision': '0'*40, 'limits': {}, 'stop_conditions': {}}
        snapshot = {'campaign': {'manifest': manifest, 'state': 'stopped',
                                 'manifest_sha256': '1'*64, 'created': 0},
                    'jobs': [{'job_id': 'blocked', 'spec': {'template_id': 'research-squad-anomalies-v1'},
                              'state': 'rejected', 'comparison_verdict': 'not-run',
                              'reason': 'release pending', 'attempts': 0},
                             {'job_id': 'unstarted', 'spec': {'template_id': 'research-member-consumers-v1'},
                              'state': 'queued', 'comparison_verdict': 'not-run', 'attempts': 0}],
                    'attempts': [], 'events': []}
        with tempfile.TemporaryDirectory() as directory:
            path = write_report(Path(directory), 'unit', snapshot)
            document = path.read_text()
            self.assertIn('LAB-005 candidate', document)
            self.assertIn('LAB-006 candidate', document)
            self.assertIn('2 requested job records; 0 physical attempts', document)
            self.assertIn('release pending', document)
            self.assertEqual(json.loads(path.with_name('report.json').read_text()), snapshot)

    def test_rejected_endpoint_and_successful_disagreement_stay_separate(self):
        job = {'template_id': 'research-member-consumers-v1'}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'workload-result.json'
            for status, verdict, exit_code in [('rejected', 'not-run', 1),
                                               ('succeeded', 'different', 0)]:
                endpoint = {'template_id': job['template_id'], 'execution_status': status,
                            'comparison_verdict': verdict,
                            'details': {'hypothesis_conclusion': 'unresolved'}}
                path.write_text(json.dumps(endpoint))
                result = w.result({}, job, directory, exit_code)
                self.assertEqual(result['execution_status'], status)
                self.assertEqual(result['comparison_verdict'], verdict)
                self.assertEqual(result['details'], endpoint['details'])


if __name__ == '__main__':
    unittest.main()
