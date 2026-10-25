#!/usr/bin/env python3
"""Redistributable rejection controls for the private capture format/driver."""
import importlib.util
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("capture", Path(__file__).with_name("pc_r5_capture.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture():
    nc, ns, cb, sb, ctx, reg, rows = 3, 17, 0x70001000, 0x70003000, 0x70005000, 0x70006000, 0x70007000
    globals_ = [(0xae235c,nc),(0xae2350,0),(0xae2364,ns),(0xae23b4,cb),
                (0xae23bc,sb),(0xde1d08,ctx),(0xb63c98,reg),(0xae2c90,1)]
    regions = [(addr,struct.pack("<I",value)) for addr,value in globals_]
    clubs, staff = bytearray(nc*581), bytearray(ns*110)
    for i in range(nc):
        struct.pack_into("<I",clubs,i*581,i)
    struct.pack_into("<I",clubs,0xcf,sb+110)
    context = bytearray(0x605)
    for off,value in [(0x5f9,0x700c0000),(0x5fd,1),(0x5f1,0x700d0000),(0x5f5,1),(0x601,0x700b0000)]:
        struct.pack_into("<I",context,off,value)
    struct.pack_into("<I",staff,110,1)
    struct.pack_into("<I",staff,110+0x39,cb)
    regions += [(cb,clubs),(sb,staff),(ctx,context),
                (0x700b0000,bytes((nc+32)*0x91)),(0x700c0000,bytes(6371)),
                (0x700d0000,bytes(6371)),(reg,struct.pack("<II",rows,16)),
                (rows,bytes(16*0xa6ef))]
    return b"PCR5SP01"+b"".join(struct.pack("<II",addr,len(data))+data for addr,data in regions)+b"PCR5DONE"

class Controls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root/"capture.bin"
    def tearDown(self):
        self.tmp.cleanup()
    def test_complete_and_truncated(self):
        raw = fixture()
        self.path.write_bytes(raw)
        self.assertEqual(m.parse_capture(self.path)["registry_count"],16)
        for bad in [raw[:-1],raw[:16],raw+b"x",raw.replace(b"PCR5SP01",b"BADMAGIC")]:
            self.path.write_bytes(bad)
            with self.assertRaises(ValueError):
                m.parse_capture(self.path)
    def test_wrong_length_and_pointer(self):
        raw = bytearray(fixture())
        struct.pack_into("<I",raw,12,0xffffffff)
        self.path.write_bytes(raw)
        with self.assertRaises(ValueError):
            m.parse_capture(self.path)
        raw = bytearray(fixture())
        # Registry global points outside every captured range.
        struct.pack_into("<I",raw,8+6*12+8,0xffffffff)
        self.path.write_bytes(raw)
        with self.assertRaises(ValueError):
            m.parse_capture(self.path)
    def test_no_reciprocal_human(self):
        raw = bytearray(fixture())
        # Manager pointer in first club row.
        struct.pack_into("<I",raw,8+8*12+8+0xcf,0)
        self.path.write_bytes(raw)
        with self.assertRaises(ValueError):
            m.parse_capture(self.path)
    def test_symlink_identity_and_reuse(self):
        self.path.write_bytes(b"x")
        alias = self.root/"alias"
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError):
            m.identity(alias)
        with self.assertRaises(FileExistsError):
            m.newdir(self.root)
    def child(self, code, timeout=240):
        with Path(sys.executable).resolve().open("rb") as f:
            return m.bounded(["/proc/self/fd/"+str(f.fileno()),"-c",code],
                             {"PATH":"/usr/bin:/bin"},self.root,timeout)
    def test_output_limit(self):
        code, streams, reason, _ = self.child("import os; os.write(1,b'x'*2000000)")
        self.assertEqual(reason,"output-limit")
        self.assertEqual(len(streams[0]),1048576)
        self.assertNotEqual(code,0)
    def test_missing_extent_count_and_overlap(self):
        raw = fixture()
        regions, pos = [], 8
        while pos < len(raw)-8:
            addr, size = struct.unpack_from("<II",raw,pos)
            regions.append((addr,raw[pos+8:pos+8+size]))
            pos += 8+size
        def encode(items):
            return b"PCR5SP01"+b"".join(struct.pack("<II",a,len(b))+b for a,b in items)+b"PCR5DONE"
        bad = []
        bad.append(regions[:13]+regions[14:])  # missing second bank
        changed = list(regions)
        changed[10] = (changed[10][0],changed[10][1][:-1])
        bad.append(changed)
        changed = list(regions)
        context = bytearray(changed[10][1])
        struct.pack_into("<I",context,0x5fd,0)
        changed[10] = (changed[10][0],bytes(context))
        bad.append(changed)
        changed = list(regions)
        changed[12] = (changed[13][0],changed[12][1])
        bad.append(changed)
        changed = list(regions)
        changed[0] = (changed[0][0],struct.pack("<I",0xffffffff))
        bad.append(changed)
        for items in bad:
            self.path.write_bytes(encode(items))
            with self.assertRaises(ValueError):
                m.parse_capture(self.path)
    def test_closed_stream_hang(self):
        code, _, reason, elapsed = self.child("import os,time; os.close(1); os.close(2); time.sleep(2)",.1)
        self.assertEqual(reason,"timeout")
        self.assertNotEqual(code,0)
        self.assertLess(elapsed,1)
    def test_timeout(self):
        code, _, reason, _ = self.child("import time; time.sleep(2)",.1)
        self.assertEqual(reason,"timeout")
        self.assertNotEqual(code,0)
if __name__ == "__main__":
    unittest.main()
