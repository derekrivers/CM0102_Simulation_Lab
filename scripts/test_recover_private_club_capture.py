#!/usr/bin/env python3
"""Redistributable corruption/provenance/bounds controls for private extraction."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('capture', Path(__file__).with_name('recover_private_club_capture.py'))
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class CaptureControls(unittest.TestCase):
    def test_wrong_identity_and_length_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'input'
            p.write_bytes(b'fictional')
            sha = hashlib.sha256(b'fictional').hexdigest()
            self.assertEqual(capture.checked_file(p, 9, sha), b'fictional')
            with self.assertRaises(ValueError):
                capture.checked_file(p, 8, sha)
            p.write_bytes(b'fictionam')
            with self.assertRaises(ValueError):
                capture.checked_file(p, 9, sha)

    def test_symlink_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, link = Path(tmp) / 'input', Path(tmp) / 'link'
            p.write_bytes(b'fictional')
            link.symlink_to(p)
            with self.assertRaises(ValueError):
                capture.checked_file(link, 9, capture.digest(b'fictional'))

    def test_pointer_crossing_or_outside_region_reject(self):
        mem = capture.Memory(b'1234', b'abcd')
        self.assertEqual(mem.read(0x70000001, 2), b'bc')
        for address, size in [(0x400003, 2), (0x6fffffff, 1), (0xffffffff, 2), (-1, 1), (0x400000, -1)]:
            with self.subTest(address=address, size=size), self.assertRaises(ValueError):
                mem.read(address, size)

    def test_name_requires_terminator_and_no_controls(self):
        for raw in (b'abcd', b'a\x01\0\0'):
            with self.assertRaises(ValueError):
                capture.Memory(raw, b'').name(0x400000, 4)

    def test_canonical_fingerprint_is_key_order_independent(self):
        self.assertEqual(capture.canonical({'z': 1, 'a': '\u00e9'}), b'{"a":"\xc3\xa9","z":1}')
        self.assertEqual(capture.canonical({'a': 2, 'z': 1}), capture.canonical({'z': 1, 'a': 2}))


if __name__ == '__main__':
    unittest.main()
