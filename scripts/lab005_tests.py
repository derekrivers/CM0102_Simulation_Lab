"""Synthetic-only LAB-005 checks. Never opens retained inputs."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab005
from lab005_decoder_a import decode as a
from lab005_decoder_b import decode as b


class DecoderTests(unittest.TestCase):
    def test_known_complete_ledger_and_mutations(self):
        controls = lab005.controls()
        self.assertEqual(len(controls), 21)
        self.assertTrue(all(row['passed'] for row in controls), controls)

    def test_full_accounting_and_secondary_flags(self):
        for decoder in (a, b):
            ledger = decoder(lab005.fixture())
            self.assertEqual(ledger, lab005.known_ledger())
            report = lab005.summarize(ledger)
            self.assertEqual(sum(report['counts']['staff_primary'].values()), 60)
            self.assertEqual(sum(report['counts']['slot_primary'].values()), 50)
            self.assertEqual(report['counts']['associated'], 51)
            self.assertEqual(report['counts']['excluded_association'], 9)
            self.assertEqual(ledger['staff'][50]['flags'], ['foreign-club', 'null-player'])
            self.assertEqual(report['hypothesis_conclusion'], 'supported')

    def test_staff_id_player_alignment_and_missing_staff(self):
        original = lab005.fixture()
        for change in ('staff-id', 'player-alignment', 'staff-missing'):
            ranges = []
            for base, raw in original:
                if base == 0x20000:
                    edited = bytearray(raw)
                    if change == 'staff-id':
                        edited[:4] = (999).to_bytes(4, 'little')
                    elif change == 'player-alignment':
                        edited[97:101] = (0x30001).to_bytes(4, 'little')
                    else:
                        # Omit the end of staff record zero while preserving the manager.
                        ranges.extend([(base, bytes(edited[:100])), (base+110, bytes(edited[110:]))])
                        continue
                    raw = bytes(edited)
                ranges.append((base, raw))
            left, right = a(ranges), b(ranges)
            self.assertEqual(left, right)
            expected = {'staff-id': 'wrong-staff-id', 'player-alignment': 'unaligned-player',
                        'staff-missing': 'missing-staff'}[change]
            self.assertEqual(left['slots'][0]['primary'], expected)
            self.assertEqual(len(left['staff']), 60)

    def test_missing_extent_censors_completeness_and_preserves_ids(self):
        for decoder in (a, b):
            ledger = decoder(lab005.fixture('truncated-record'))
            self.assertEqual(ledger['slots'][49]['player_id'], 49)
            self.assertEqual(ledger['slots'][49]['flags'], ['missing-player'])
            self.assertEqual(lab005.summarize(ledger)['hypothesis_conclusion'], 'unresolved')
            self.assertEqual(lab005.summarize(ledger)['observation_status'], 'censored')

    def test_duplicate_and_omission_are_not_dropped(self):
        for decoder in (a, b):
            for mutation in ('duplicate-slot', 'omitted-slot'):
                ledger = decoder(lab005.fixture(mutation))
                result = lab005.summarize(ledger)
                self.assertEqual(result['counts']['slots'], 50)
                self.assertEqual(result['counts']['inverse_only'], 1)
                self.assertEqual(result['counts']['listed_candidates'], 49)
            self.assertEqual(lab005.summarize(decoder(lab005.fixture('duplicate-slot')))
                             ['hypothesis_conclusion'], 'contradicted')

    def test_overlap_missing_globals_and_nonlinked_identity(self):
        for decoder in (a, b):
            with self.assertRaises(ValueError):
                decoder(lab005.fixture()+[(0x30000, b'overlap')])
            with self.assertRaises(ValueError) as failure:
                decoder([(base, raw) for base, raw in lab005.fixture() if base != 0xae2364])
            self.assertIsNone(failure.exception.dimensions)
            # Player 49 remains in the complete table but loses all staff links.
            ranges = []
            for base, raw in lab005.fixture():
                edited = bytearray(raw)
                if base == 0x20000:
                    edited[49*110+97:49*110+101] = bytes(4)
                if base == 0x30000:
                    edited[49*70:49*70+4] = (999).to_bytes(4, 'little')
                ranges.append((base, bytes(edited)))
            result = lab005.summarize(decoder(ranges))
            self.assertEqual(result['counts']['list_only'], 0)
            self.assertEqual(result['counts']['inverse_only'], 0)
            self.assertEqual(result['hypothesis_conclusion'], 'unresolved')
            self.assertEqual(result['hypothesis_reason'], 'inconsistent-table-identities')

    def test_incomplete_binding_search_cannot_claim_uniqueness(self):
        for missing in ('other-club-manager', 'reserved-manager-id', 'reserved-manager-club', 'selected-club-id'):
            ranges = []
            for base, raw in lab005.fixture():
                if base == 0xae235c:
                    raw = (4).to_bytes(4, 'little')  # Two ordinary clubs.
                hole = None
                if missing == 'other-club-manager' and base == 0x10000:
                    hole = 581+207
                elif missing == 'reserved-manager-id' and base == 0x20000:
                    hole = 59*110
                elif missing == 'reserved-manager-club' and base == 0x20000:
                    hole = 59*110+57
                elif missing == 'selected-club-id' and base == 0x10000:
                    hole = 0
                if hole is None:
                    ranges.append((base, raw))
                else:
                    if hole:
                        ranges.append((base, raw[:hole]))
                    ranges.append((base+hole+4, raw[hole+4:]))
            for decoder in (a, b):
                with self.subTest(missing=missing, decoder=decoder.__module__):
                    with self.assertRaisesRegex(ValueError, 'incomplete-binding-search') as failure:
                        decoder(ranges)
                    self.assertEqual(failure.exception.dimensions,
                                     {'clubs': 4, 'nations': 1, 'staff': 60, 'players': 50})

    def test_exact_comparator_keeps_order_types_and_values(self):
        expected = {'slots': [1, 2], 'signed': -1}
        for actual in ({'slots': [2, 1], 'signed': -1},
                       {'slots': [1, 2], 'signed': 4294967295},
                       {'slots': [1], 'signed': -1},
                       {'slots': [1, 2], 'signed': True}):
            self.assertTrue(lab005.exact_differences(expected, actual))
        self.assertFalse(lab005.exact_differences(expected, expected))

    def test_specimen_rejection_is_private_and_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture, attempt = root/'secret-capture', root/'attempt'
            capture.mkdir()
            attempt.mkdir()
            (capture/'image.bin').write_bytes(b'wrong')
            result = lab005.run(capture, attempt)
            self.assertEqual(result['execution_status'], 'rejected')
            self.assertEqual(result['comparison_verdict'], 'not-run')
            self.assertEqual(result['details']['decoder_counts'],
                             {'planned': 2, 'completed': 0, 'failed': 0, 'unstarted': 2})
            self.assertEqual(result['details']['accounting'][0]['planned_slots'], 50)
            public = json.dumps(result)
            self.assertNotIn(directory, public)
            self.assertNotIn('secret-capture', public)
            self.assertTrue((attempt/'lab005-private'/'failure.json').exists())
            with self.assertRaises(FileExistsError):
                lab005.run(capture, attempt)


if __name__ == '__main__':
    unittest.main()
