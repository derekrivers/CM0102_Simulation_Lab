#!/usr/bin/env python3
"""Synthetic structural/identity controls; never real-state qualification."""
import struct
import tempfile
import unittest
from pathlib import Path
from qualify_human_registry import locate, checked, digest, GLOBALS, REGISTRY_STRIDE
from qualify_fresh_human_registry import SparseSnapshot

class Memory:
    def __init__(self):
        self.base=0x70000000;self.heap=bytearray(2000000);self.globals={}
        clubs,nations,staff,cb,sb,ctx,registry=20,5,100,self.base,self.base+20000,self.base+40000,self.base+50000
        self.globals=dict(zip(GLOBALS,[clubs,nations,staff,cb,sb,ctx,registry]))
        self.put(registry,self.base+60000);self.put(registry+4,16)
        for i in range(clubs):self.put(cb+i*581,i)
        for i in range(staff):self.put(sb+i*110,i)
        self.club=cb+7*581;self.manager=sb+99*110
        self.put(self.club+0xcf,self.manager);self.put(self.manager+0x39,self.club)
        for offset,value in [(0x5fd,1),(0x5f5,1),(0x5f9,self.base+800000),(0x5f1,self.base+810000),(0x601,self.base+820000)]:self.put(ctx+offset,value)
    def put(self,a,v):struct.pack_into('<I',self.heap,a-self.base,v)
    def read(self,a,n):
        if a in self.globals and n==4:return struct.pack('<I',self.globals[a])
        if not self.base<=a<=a+n<=self.base+len(self.heap):raise ValueError('outside synthetic extent')
        return bytes(self.heap[a-self.base:a-self.base+n])
    def u32(self,a):return struct.unpack('<I',self.read(a,4))[0]
    def s32(self,a):return struct.unpack('<i',self.read(a,4))[0]
    def s16(self,a):return struct.unpack('<h',self.read(a,2))[0]

class Controls(unittest.TestCase):
    def test_real_identity_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input';p.write_bytes(b'fixture')
            self.assertEqual(checked(p,digest(b'fixture')),b'fixture')
            with self.assertRaises(ValueError):checked(p,digest(b'altered'))
    def test_reserved_identity_and_reciprocal_binding(self):
        for target,value in [('id',98),('reciprocal',0),('unaligned',1)]:
            m=Memory();self.assertEqual(locate(m)['registry_index'],15)
            if target=='id':m.put(m.manager,value)
            elif target=='reciprocal':m.put(m.manager+0x39,value)
            else:m.put(m.club+0xcf,m.manager+value)
            with self.subTest(target=target),self.assertRaises(ValueError):locate(m)
    def test_count_truncation_and_pointer_bounds(self):
        for target in ['count','truncated','pointer','missing']:
            m=Memory();reg=m.globals[0xb63c98]
            if target=='count':m.put(reg+4,17)
            elif target=='truncated':m.heap=m.heap[:700000]
            elif target=='pointer':m.put(reg,0xfffffff0)
            else:m.globals[0xb63c98]=0
            with self.subTest(target=target),self.assertRaises(ValueError):locate(m)
    def test_invalid_existing_slot_rejects(self):
        m=Memory();row=m.base+60000+15*REGISTRY_STRIDE;m.heap[row-m.base+0x9a69]=255
        with self.assertRaises(ValueError):locate(m)

    def test_sparse_completeness_identity_and_region_overlap(self):
        m=Memory();cb=m.globals[0xae23b4];sb=m.globals[0xae23bc]
        ctx=m.globals[0xde1d08];reg=m.globals[0xb63c98]
        regions=[(a,m.read(a,4)) for a in GLOBALS]+[(0xae2c90,bytes(4))]+[
            (cb,m.read(cb,20*581)),(sb,m.read(sb,100*110)),(ctx,m.read(ctx,0x605)),
            (m.u32(ctx+0x601),m.read(m.u32(ctx+0x601),52*0x91)),
            (m.u32(ctx+0x5f9),m.read(m.u32(ctx+0x5f9),6371)),
            (m.u32(ctx+0x5f1),m.read(m.u32(ctx+0x5f1),6371)),
            (reg,m.read(reg,8)),(m.u32(reg),m.read(m.u32(reg),16*REGISTRY_STRIDE))]
        def encode(rs):
            return b'PCR5SP01'+b''.join(struct.pack('<II',a,len(b))+b for a,b in rs)+b'PCR5DONE'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'capture';valid=encode(regions);p.write_bytes(valid)
            self.assertEqual(locate(SparseSnapshot(p,digest(valid)))['registry_index'],15)
            with self.assertRaises(ValueError):SparseSnapshot(p,digest(b'wrong'))
            for raw in [valid[:-1],encode(regions[:-1]),encode(regions[:-1]+[regions[-2]])]:
                p.write_bytes(raw)
                with self.assertRaises(ValueError):SparseSnapshot(p,digest(raw))

if __name__=='__main__':unittest.main()
