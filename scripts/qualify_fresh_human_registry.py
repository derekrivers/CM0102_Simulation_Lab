#!/usr/bin/env python3
"""Replay sealed sparse R5 data with the official R4 oracle. Never self-admits a fixture."""
import argparse
import json
import struct
from pathlib import Path
from qualify_human_registry import (generate,checked,digest,require,canonical,GLOBALS,
                                    HEAP_BASE,REGISTRY_STRIDE)

class SparseSnapshot:
    def __init__(self, path, expected):
        require(path.stat().st_size <= 16778000, 'sparse capture too large')
        data=checked(path,expected)
        require(data[:8]==b'PCR5SP01' and data[-8:]==b'PCR5DONE','incomplete sparse capture')
        self.regions=[];pos=8
        while pos<len(data)-8:
            require(pos+8<=len(data)-8,'truncated sparse header')
            address,size=struct.unpack_from('<II',data,pos);pos+=8
            require(0<size<=8388608 and address+size<=2**32 and pos+size<=len(data)-8,
                    'unsupported sparse extent')
            require(not any(address<a+len(b) and a<address+size for a,b in self.regions),
                    'overlapping sparse extents')
            self.regions.append((address,data[pos:pos+size]));pos+=size
        require(pos==len(data)-8 and len(self.regions)==16,'wrong sparse region count')
        require([(a,len(b)) for a,b in self.regions[:8]]==[(a,4) for a in GLOBALS]+[(0xae2c90,4)],
                'wrong sparse globals')
        self.segments=sorted(self.regions[8:])
        require(all(HEAP_BASE<=a<a+len(b)<=0xef000000 for a,b in self.segments),'unsupported sparse heap')
        self.sha256=digest(data)
    def read(self,address,size):
        require(size>=0 and address>=0 and address+size<=2**32,'invalid sparse read')
        for base,data in self.regions:
            if base<=address and address+size<=base+len(data):return data[address-base:address-base+size]
        raise ValueError('uncaptured sparse read')
    def u32(self,address):return struct.unpack('<I',self.read(address,4))[0]
    def s32(self,address):return struct.unpack('<i',self.read(address,4))[0]
    def s16(self,address):return struct.unpack('<h',self.read(address,2))[0]

def run(binary,path,expected,output,build_receipt):
    snapshot=SparseSnapshot(path,expected)
    # Build receipt is a separately sealed R5 prerequisite, not a caller-chosen
    # platform label. Verify its fixed source pin and derivative binary identity.
    metadata=json.loads(build_receipt.read_bytes())
    require(metadata['source']['revision']=='144ed82c248228c7769c6785899527eae5b33c3d','wrong R5 platform')
    identity={'source_capture_sha256':snapshot.sha256,'source_identity_scheme':'SHA256 of complete sparse capture artifact',
              'platform_revision':metadata['source']['revision'],
              'instrumented_binary_sha256':metadata['instrumented']['sha256'],
              'build_receipt_sha256':digest(build_receipt.read_bytes()),
              'qualification':'R5 sparse observed input; campaign receipt required separately',
              'captured_regions':len(snapshot.regions)}
    receipt,fixture=generate(binary,path,snapshot,identity)
    receipt['method']='official entry-to-return instructions over complete declared sparse regions; no stubbed callees'
    receipt['state']['captured_heap_region_bytes']=receipt['state'].pop('complete_heap_bytes')
    receipt['complete_captured_regions_and_image_checked']=receipt.pop('complete_heap_and_image_checked')
    receipt['production_admission']='not-admitted; separate reviewed fixture fingerprint required'
    receipt['limitations'][0]='Sparse captured regions only, not the complete runtime heap; every oracle data read is admitted inside captured regions'
    receipt['limitations'].append('Execution endpoint, contemporaneous seals, input-consumption gap and instrumentation comparison are in the separate R5 campaign receipt')
    with output.open('x',encoding='utf8') as out:out.write(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'successful_calls':receipt['successful_calls'],'starts':receipt['successful_instruction_starts'],
                      'oracle_sha256':digest(output.read_bytes()),'fresh_fixture_sha256':digest(canonical(fixture)),
                      'production_admission':'not-admitted'}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary',type=Path);p.add_argument('capture',type=Path);p.add_argument('capture_sha256')
    p.add_argument('build_receipt',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.binary,a.capture,a.capture_sha256,a.output,a.build_receipt)
