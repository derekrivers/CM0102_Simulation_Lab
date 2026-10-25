"""Invented admission evidence only; no live state, decoder or worker is invoked."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import admission as a
import core
import workloads as w


class Admission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = {'schema_version': 1, 'campaign_id': 'pilot', 'profile_id': 'research-anomalies',
                         'source_revision': 'a'*40, 'pins': [], 'observation_seconds': 0,
                         'limits': dict(a.LIMITS), 'stop_conditions': {'max_failures': 1, 'stop_on_divergence': True},
                         'jobs': [{'job_id': '001-research-squad-anomalies-v1',
                                   'template_id': 'research-squad-anomalies-v1', 'parameters': {}, 'pins': []}],
                         'provenance': {'source_dirty': False, 'research_state_root': str(self.root)}}

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        path = self.root/name
        path.write_bytes(a.canonical(data) + b'\n')
        return a.reference(path)

    def review(self):
        return self.write('review.json', {'schema_version': 1, 'kind': 'research-operational-review-v1',
                          'decision': 'approved-for-pilot', 'source_revision': 'a'*40, 'campaign_id': 'pilot',
                          'reviewer': 'synthetic-reviewer', 'implementation_author': 'synthetic-author',
                          'frozen_subject_sha256': a.subject(self.manifest)})

    def test_unadmitted_manifest_cannot_configure_or_validate_job(self):
        with self.assertRaisesRegex(ValueError, 'release blocked'):
            w.validate(self.manifest, self.root, {})
        with self.assertRaisesRegex(ValueError, 'release blocked'):
            w.validate_job(self.manifest, self.manifest['jobs'][0], self.root, {})

    def test_claims_and_interim_receipt_cannot_release(self):
        for kind, decision in [('qualification-interim-audit-v1', 'incomplete'),
                               ('qualification-acceptance-v1', 'censored'),
                               ('qualification-acceptance-v1', 'failed')]:
            ref = self.write('acceptance.json', {'schema_version': 1, 'kind': kind, 'decision': decision})
            with self.assertRaisesRegex(ValueError, 'not independently accepted'):
                a.qualification(ref)

    def test_review_binds_limits_job_config_and_source(self):
        self.manifest['provenance']['pilot_admission'] = {'operational_review': self.review(),
                                                        'qualification_acceptance': {}}
        # Evidence validation is covered separately; this isolates subject binding.
        with patch.object(a, 'qualification'), patch.object(a, 'clean_source'), patch.object(a, 'reservation'):
            a.validate(self.manifest, self.root)
            for change in ('source', 'limits', 'job', 'config', 'reviewer'):
                manifest = copy.deepcopy(self.manifest)
                if change == 'source':
                    manifest['source_revision'] = 'b'*40
                elif change == 'limits':
                    manifest['limits']['disk_bytes'] *= 2
                elif change == 'job':
                    manifest['jobs'].append(copy.deepcopy(manifest['jobs'][0]))
                elif change == 'config':
                    manifest['provenance']['config_sha256'] = 'f'*64
                else:
                    review = a.read_reference(self.manifest['provenance']['pilot_admission']['operational_review'])
                    review['reviewer'] = review['implementation_author']
                    manifest['provenance']['pilot_admission']['operational_review'] = self.write('self-review.json', review)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    a.validate(manifest, self.root)

    def test_unicode_matches_core_canonical_and_replay_subject(self):
        self.manifest['provenance']['note'] = 'frozen café'
        self.assertEqual(a.canonical(self.manifest), core.canonical(self.manifest).encode())
        self.manifest['provenance']['pilot_admission'] = {'operational_review': self.review(),
                                                        'qualification_acceptance': {}}
        replay = copy.deepcopy(self.manifest)
        replay['campaign_id'] = 'pilot-replay-123'
        replay['provenance']['replay_of'] = {'campaign_id': 'pilot', 'job_id': self.manifest['jobs'][0]['job_id'],
            'manifest_sha256': hashlib.sha256(core.canonical(self.manifest).encode()).hexdigest()}
        self.assertEqual(a.subject(replay), a.subject(self.manifest))
        with patch.object(a, 'qualification'), patch.object(a, 'clean_source'), patch.object(a, 'reservation'):
            a.validate(replay, self.root)
            replay['provenance']['replay_of']['manifest_sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'replay differs'):
                a.validate(replay, self.root)

    def test_real_allocation_consumption_recovery_and_replay_bound(self):
        # Tiny physical allocation tests the real filesystem mechanism, not the
        # production 536 MiB reservation. No real input or heavy lock is used.
        with patch.object(a, 'TOTAL_RESERVE', 5*4096), patch.object(a, 'ATTEMPT_RESERVE', 4096):
            first = a.reservation(self.manifest, create=True)
            allocation = Path(first['path'])
            self.assertGreaterEqual(allocation.stat().st_blocks*512, 5*4096)
            attempt = {'attempt_id': 'a', 'campaign_id': 'pilot', 'ordinal': 1,
                       'directory': str(self.root/'attempts/a')}
            once = a.reservation(self.manifest, attempt=attempt)
            self.assertEqual(once['reserved_bytes'], 4*4096)
            self.assertEqual(a.reservation(self.manifest, attempt=attempt), once)
            replay = copy.deepcopy(self.manifest)
            replay['provenance']['replay_of'] = {'dummy': True}
            replay['campaign_id'] = 'replay-one'
            attempt.update(attempt_id='b', campaign_id='replay-one', directory=str(self.root/'attempts/b'))
            a.reservation(replay, attempt=attempt)
            replay['campaign_id'] = 'replay-two'
            attempt.update(attempt_id='c', campaign_id='replay-two', directory=str(self.root/'attempts/c'))
            with self.assertRaisesRegex(ValueError, 'one pilot and one replay'):
                a.reservation(replay, attempt=attempt)
            allocation.unlink()
            with allocation.open('wb') as stream:
                stream.truncate(3*4096)
            with self.assertRaisesRegex(ValueError, 'sparse or unallocated'):
                a.reservation(self.manifest)

    def test_no_reservation_when_insufficient_space(self):
        with patch.object(a.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 1})()):
            with self.assertRaisesRegex(ValueError, 'insufficient reserved disk'):
                a.reservation(self.manifest, create=True)
        self.assertEqual(list((self.root/'research-reservations').glob('*.reserve')), [])

    def test_four_attempt_budget_and_journal_before_truncate_recovery(self):
        with patch.object(a, 'TOTAL_RESERVE', 5*4096), patch.object(a, 'ATTEMPT_RESERVE', 4096):
            reserved = a.reservation(self.manifest, create=True)
            record = Path(reserved['path']).with_suffix('.json')
            state = json.loads(record.read_text())
            state['consumed']['interrupted'] = {'campaign_id': 'pilot', 'ordinal': 1}
            state['pilot_campaign'] = 'pilot'
            record.write_bytes(a.canonical(state))  # Simulate death after durable journal, before truncate.
            attempt = {'attempt_id': 'interrupted', 'campaign_id': 'pilot', 'ordinal': 1,
                       'directory': str(self.root/'attempts/interrupted')}
            self.assertEqual(a.reservation(self.manifest, attempt=attempt)['reserved_bytes'], 4*4096)
            for index in range(1, 4):
                manifest = copy.deepcopy(self.manifest)
                campaign = 'pilot' if index == 1 else 'selected-replay'
                if index > 1:
                    manifest['provenance']['replay_of'] = {'dummy': True}
                attempt.update(attempt_id=str(index), campaign_id=campaign, ordinal=2 if index in (1,3) else 1,
                               directory=str(self.root/'attempts'/str(index)))
                a.reservation(manifest, attempt=attempt)
            self.assertEqual(Path(reserved['path']).stat().st_size, 4096)
            attempt.update(attempt_id='fifth', directory=str(self.root/'attempts/fifth'))
            with self.assertRaisesRegex(ValueError, 'reservation exhausted'):
                a.reservation(manifest, attempt=attempt)

    def qualification_fixture(self):
        # Complete synthetic files have real hashes and immutable publications.
        (self.root/'config.json').write_text('{}')
        source = self.root/'source/tools/lab/core.py'
        source.parent.mkdir(parents=True)
        source.write_text('# synthetic source\n')
        jobs = [{'job_id': name, 'template_id': name[4:], 'parameters': {}, 'pins': []}
                for name in (a.RNG_JOB, '002-original-r10-regression-v1', '003-bosman-same-save-v1')]
        manifest = {'schema_version': 1, 'campaign_id': a.QUALIFICATION_ID,
                    'source_revision': a.QUALIFICATION_SOURCE, 'pins': [a.reference(source)], 'jobs': jobs,
                    'observation_seconds': 86400, 'provenance': {'config_sha256': hashlib.sha256(b'{}').hexdigest()}}
        original_sha = hashlib.sha256(a.canonical(manifest)).hexdigest()
        raw = b'x'*75952
        rng_sha = hashlib.sha256(raw).hexdigest()
        facts = [{'native_sha256': rng_sha, 'wasm_sha256': rng_sha, 'canonical_bytes': 75952,
                  'negative_control_mismatches': [1023,61,2447,123]},
                 {'successful_calls': 11, 'censored_calls': 4, 'controls': {str(i): True for i in range(12)}},
                 {'endpoint': 'classic-same-save-normal-again-14-days-equal'}]

        def snapshot(value, end, replay=False):
            attempts, rows = [], []
            for index, job in enumerate(value['jobs']):
                directory = self.root/'attempts'/('replay' if replay else str(index))
                directory.mkdir(parents=True)
                details = copy.deepcopy(facts[index])
                if index == 0:
                    (directory/'native.stdout').write_bytes(raw)
                    (directory/'wasm.bin').write_bytes(raw)
                details['artifacts'] = core.artifact_inventory(directory)
                verdict = 'not-run' if index == 2 else 'equal'
                result = {'execution_status': 'succeeded', 'comparison_verdict': verdict, 'details': details}
                (directory/'result.json').write_bytes(a.canonical(result) + b'\n')
                attempts.append({'attempt_id': directory.name, 'directory': str(directory), 'job_id': job['job_id'],
                                 'publication_state': 'published', 'finished': end-1, 'execution_status': 'succeeded',
                                 'comparison_verdict': verdict, 'result': result})
                rows.append({'job_id': job['job_id'], 'state': 'succeeded', 'execution_status': 'succeeded', 'spec': job})
            return {'campaign': {'campaign_id': value['campaign_id'], 'manifest': value,
                     'manifest_sha256': hashlib.sha256(a.canonical(value)).hexdigest(), 'state': 'completed',
                     'stop_reason': None, 'observation_started': end-(2 if replay else 86400),
                     'observation_qualified': 1, 'observation_elapsed_seconds': 86400},
                    'jobs': rows, 'attempts': attempts, 'events': [{'kind': 'completed', 'time': end}]}

        original = snapshot(manifest, 1793026606)
        replay_manifest = copy.deepcopy(manifest)
        replay_manifest.update(campaign_id='selected-replay', observation_seconds=0, jobs=[jobs[0]])
        replay_manifest['provenance']['replay_of'] = {'campaign_id': a.QUALIFICATION_ID,
            'job_id': a.RNG_JOB, 'manifest_sha256': original_sha}
        replay = snapshot(replay_manifest, 1793026609, replay=True)
        receipt = {'schema_version': 1, 'kind': 'qualification-acceptance-v1', 'decision': 'passed',
                   'reviewer': 'synthetic-reviewer', 'implementation_author': 'synthetic-author',
                   'observed_at_utc': '2026-10-26T15:00:00Z', 'source_revision': a.QUALIFICATION_SOURCE,
                   'campaign_id': a.QUALIFICATION_ID, 'manifest_sha256': original_sha, 'selected_job_id': a.RNG_JOB,
                   'evidence': {'completion_snapshot': self.write('complete.json', original),
                                'completion_report': self.write('report.json', original),
                                'replay_snapshot': self.write('replay.json', replay),
                                'replay_manifest': self.write('replay-manifest.json', replay_manifest)}}
        return receipt, original_sha, rng_sha

    def test_acceptance_requires_actual_evidence_and_raw_rng(self):
        receipt, original_sha, rng_sha = self.qualification_fixture()
        ref = self.write('accepted.json', receipt)
        with patch.object(a, 'QUALIFICATION_SHA', original_sha), patch.object(a, 'RNG_SHA', rng_sha), \
                patch.object(a, 'clean_source'):
            self.assertEqual(a.qualification(ref), receipt)
            raw = self.root/'attempts/replay/native.stdout'
            raw.write_bytes(b'y'*75952)
            with self.assertRaisesRegex(ValueError, 'inventory changed'):
                a.qualification(ref)

    def test_incomplete_horizon_and_early_replay_reject_even_passed_receipt(self):
        receipt, original_sha, rng_sha = self.qualification_fixture()
        with patch.object(a, 'QUALIFICATION_SHA', original_sha), patch.object(a, 'RNG_SHA', rng_sha), \
                patch.object(a, 'clean_source'):
            original = a.read_reference(receipt['evidence']['completion_snapshot'])
            original['campaign']['observation_elapsed_seconds'] = 86399
            receipt['evidence']['completion_snapshot'] = self.write('complete.json', original)
            receipt['evidence']['completion_report'] = self.write('report.json', original)
            with self.assertRaisesRegex(ValueError, 'horizon incomplete'):
                a.qualification(self.write('accepted.json', receipt))
            original['campaign']['observation_elapsed_seconds'] = 86400
            receipt['evidence']['completion_snapshot'] = self.write('complete.json', original)
            receipt['evidence']['completion_report'] = self.write('report.json', original)
            replay = a.read_reference(receipt['evidence']['replay_snapshot'])
            replay['campaign']['observation_started'] = 1793026605
            receipt['evidence']['replay_snapshot'] = self.write('replay.json', replay)
            with self.assertRaisesRegex(ValueError, 'after actual completion'):
                a.qualification(self.write('accepted.json', receipt))


if __name__ == '__main__':
    unittest.main()
