#!/usr/bin/env python3
"""Small synthetic parser controls; these never qualify real input."""
import struct
import unittest
from pc_r10_projection_inventory import Memory, inventory


class Controls(unittest.TestCase):
    def rejects(self, operation):
        with self.assertRaises(ValueError):
            operation()

    def test_overlapping_and_duplicate_regions(self):
        self.rejects(lambda: Memory([(8, b'ab'), (9, b'cd')]))
        self.rejects(lambda: Memory([(8, b'a'), (8, b'a')]))

    def test_missing_extent_and_no_cross_region_read(self):
        memory = Memory([(8, b'ab'), (10, b'cd')])
        self.rejects(lambda: memory.read(9, 2))
        self.rejects(lambda: memory.read(7, 1))

    def test_signedness_and_width(self):
        memory = Memory([(8, b'\xff'*4)])
        self.assertEqual(memory.i32(8), -1)
        self.assertEqual(memory.u32(8), 2**32-1)
        self.rejects(lambda: memory.u32(9))

    def test_address_overflow_and_negative_size(self):
        self.rejects(lambda: Memory([(2**32-1, b'ab')]))
        memory = Memory([(8, b'ab')])
        self.rejects(lambda: memory.read(8, -1))
        self.rejects(lambda: memory.read(2**32-1, 2))

    def test_count_caps_before_table_reads(self):
        ranges = [(address, struct.pack('<I', count)) for address, count in
                  [(0xae235c, 10001), (0xae2350, 1), (0xae2364, 17)]]
        self.rejects(lambda: inventory(Memory(ranges)))


if __name__ == '__main__':
    unittest.main()
