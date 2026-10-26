"""Light synthetic controls only. Never opens an original executable/capture."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import lab006


class ConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capstone, cls.decoder = lab006.qualified_decoder()

    def decode(self, code):
        return lab006.decode(code, 0x1000, 0x1000 + len(code), self.capstone, self.decoder)

    def test_all_discriminating_controls(self):
        controls = lab006.controls(self.capstone, self.decoder)
        self.assertEqual(len(controls), 11)
        self.assertTrue(all(controls.values()))

    def test_branch_into_middle_rejected(self):
        # jne lands on the second byte of a following MOV immediate.
        with self.assertRaisesRegex(lab006.AdmissionError, "branch_into_instruction"):
            self.decode(bytes.fromhex("7501b800000000"))

    def test_incomplete_decode_never_silently_drops_tail(self):
        with self.assertRaisesRegex(lab006.AdmissionError, "incomplete_linear_decode"):
            self.decode(bytes.fromhex("90e800"))

    def test_read_width_and_lea_are_distinct(self):
        rows = self.decode(bytes.fromhex("8a088b088d08"))
        self.assertEqual(rows[0]["operands"][1]["width_bits"], 8)
        self.assertEqual(rows[1]["operands"][1]["width_bits"], 32)
        self.assertTrue(rows[0]["operands"][1]["read"])
        self.assertTrue(rows[1]["operands"][1]["read"])
        self.assertTrue(rows[2]["operands"][1]["address_only"])
        self.assertFalse(rows[2]["operands"][1]["read"])

    def test_branch_signedness_and_stack_call(self):
        rows = self.decode(bytes.fromhex("7c0072007400e800000000"))
        self.assertEqual([row["signedness"] for row in rows[:3]],
                         ["signed-comparison", "unsigned-comparison", "equality-bit-pattern"])
        self.assertEqual(rows[-1]["implicit_memory"],
                         [{"kind": "stack", "operation": "write", "width_bits": 32}])
        self.assertFalse(rows[-1]["target_inside_excerpt"])

    def test_specimen_rejection_retains_separate_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory)
            specimen = attempt / "invented-small-input"
            specimen.write_bytes(b"not an original executable")
            outcome = lab006.run(specimen, attempt)
            self.assertEqual(outcome["execution_status"], "rejected")
            self.assertEqual(outcome["comparison_verdict"], "not-run")
            self.assertEqual(outcome["details"]["hypothesis_conclusion"], "unresolved")
            self.assertEqual(outcome["details"]["planned_case_count"], 2)
            self.assertEqual(outcome["details"]["unstarted_case_count"], 2)
            self.assertEqual(outcome["details"]["original_instructions_executed"], 0)
            raw = json.loads((attempt / "lab006-private.json").read_text())
            public = json.loads((attempt / "lab006-result.json").read_text())
            self.assertEqual(outcome, public)
            self.assertEqual(raw["ranges"], [])
            self.assertEqual(len(raw["controls"]), 11)
            self.assertNotIn(directory, json.dumps(public))
            self.assertNotIn("instructions", public["details"])
            before = (attempt / "lab006-private.json").read_bytes()
            with self.assertRaisesRegex(lab006.AdmissionError, "artifact_exists"):
                lab006.run(specimen, attempt)
            self.assertEqual(before, (attempt / "lab006-private.json").read_bytes())

    def test_decoder_mismatch_fails_closed(self):
        with patch.object(self.capstone, "__version__", "0.0"):
            with self.assertRaisesRegex(lab006.AdmissionError, "decoder_version_rejected"):
                lab006.qualified_decoder()

    def test_pe_invalid_input_rejected_without_decode(self):
        with self.assertRaises(lab006.AdmissionError):
            lab006.pe_ranges(bytes(128))

    def test_frozen_range_seals_match_retained_reviewed_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
                              "docs/research/evidence/pc-r10-command-static-v1.json").read_text())
        for entry, prior_name in zip(lab006.RANGES, ("fifty_member_count_excerpt",
                                                    "membership_assignment_caller_excerpt")):
            _, start, end, digest, count = entry
            prior = receipt["ranges"][prior_name]
            self.assertEqual((f"{start:08x}", f"{end:08x}", digest, count),
                             (prior["start"], prior["end_exclusive"], prior["sha256"],
                              prior["decoded_instructions"]))


if __name__ == "__main__":
    unittest.main()
