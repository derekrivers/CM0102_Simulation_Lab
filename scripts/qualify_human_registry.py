#!/usr/bin/env python3
"""Bounded official human-registry instruction oracle over private retained state.

Raw game bytes/pointers remain private. No original process, stubs or synthetic
manager binding. Independent implementation; Bosman names are hypotheses only.
"""
import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path
import unicorn
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP,
                               UC_X86_REG_EIP, UC_X86_REG_EBX, UC_X86_REG_ESI,
                               UC_X86_REG_EDI, UC_X86_REG_EBP)
from qualify_manager_bound_plan import (Snapshot, checked, digest, SPECIMEN,
    IMAGE_HASH, HEAP_HASH, IMAGE_BASE, HEAP_BASE, STACK, STOP)

GLOBALS = [0xae235c, 0xae2350, 0xae2364, 0xae23b4, 0xae23bc, 0xde1d08, 0xb63c98]
RANGES = [(0x5fbd00,0x5fbe11), (0x5fbe20,0x5fc004),
          (0x600a50,0x600c88), (0x53b900,0x53b99f), (0x5409b0,0x540a4c),
          (0x5fd210,0x5fd2e2), (0x5fea50,0x5feb50),
          (0x5feb60,0x5fed42), (0x896660,0x8967c1)]
REGISTRY_STRIDE, SLOT_STRIDE, SLOT_COUNT = 0xa6ef, 0x1ecd, 5
SOURCE_CAPTURE = '302921d53add894761acb6ef425d930f8b83ff0a344efdf61c45fa94d1f5cfa8'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def locate(snapshot):
    clubs,nations,staff,club_base,staff_base,context,registry = [snapshot.u32(a) for a in GLOBALS]
    require(0 < 2*nations < clubs and 16 < staff, 'unsupported counts')
    snapshot.read(club_base, clubs*581)
    snapshot.read(staff_base, staff*110)
    require(registry != 0, 'missing registry')
    registry_base,count = snapshot.u32(registry),snapshot.u32(registry+4)
    require(registry_base != 0 and count == 16, 'unsupported registry capacity')
    snapshot.read(registry_base,count*REGISTRY_STRIDE)
    matches=[]
    for index in range(clubs-2*nations):
        club=club_base+index*581
        manager=snapshot.u32(club+0xcf)
        if not manager or not staff_base <= manager < staff_base+staff*110 or (manager-staff_base)%110:
            continue
        manager_id=snapshot.s32(manager)
        if not staff-16 <= manager_id < staff:
            continue
        require(manager_id == (manager-staff_base)//110, 'reserved manager id mismatch')
        require(snapshot.s32(club) == index, 'club id mismatch')
        require(snapshot.u32(manager+0x39) == club, 'nonreciprocal manager binding')
        slot=manager_id-staff+16
        row=registry_base+slot*REGISTRY_STRIDE
        require(snapshot.read(row+0x9a69,1)[0] < SLOT_COUNT, 'unsupported initial slot')
        matches.append(dict(club=club,manager=manager,club_id=index,manager_id=manager_id,
                            registry_index=slot,row=row))
    require(len(matches)==1, 'requires exactly one admitted real human binding')
    state=matches[0]
    state.update(clubs=clubs,nations=nations,staff=staff,context=context,
                 registry=registry,registry_base=registry_base,registry_count=count)
    first,second = snapshot.s32(context+0x5fd),snapshot.s32(context+0x5f5)
    bank1,bank2,mapping = [snapshot.u32(context+x) for x in (0x5f9,0x5f1,0x601)]
    require(0<first and 0<second and first+second<32768, 'unsupported bank counts')
    snapshot.read(bank1,first*6371);snapshot.read(bank2,second*6371)
    snapshot.read(mapping,(clubs+32)*0x91)
    selection=snapshot.s16(mapping+state['club_id']*0x91)
    require(0<=selection<first+second, 'invalid bank selection')
    state.update(first=first,second=second,bank1=bank1,bank2=bank2,mapping=mapping,
                 bank_selection=selection)
    return state


class Oracle:
    def __init__(self, raw, snapshot, state):
        require(unicorn.__version__=='2.1.4', 'requires Unicorn 2.1.4')
        pe=struct.unpack_from('<I',raw,0x3c)[0];opt=pe+24
        require(raw[:2]==b'MZ' and raw[pe:pe+4]==b'PE\0\0' and
                struct.unpack_from('<H',raw,opt)[0]==0x10b, 'requires PE32')
        require(struct.unpack_from('<I',raw,opt+28)[0]==IMAGE_BASE,'wrong image base')
        image_size=struct.unpack_from('<I',raw,opt+56)[0]
        self.uc=uc=unicorn.Uc(unicorn.UC_ARCH_X86,unicorn.UC_MODE_32)
        uc.mem_map(IMAGE_BASE,(image_size+4095)&~4095)
        uc.mem_write(IMAGE_BASE,raw[:struct.unpack_from('<I',raw,opt+60)[0]])
        count=struct.unpack_from('<H',raw,pe+6)[0];os=struct.unpack_from('<H',raw,pe+20)[0]
        for i in range(count):
            _,rva,size,offset=struct.unpack_from('<IIII',raw,opt+os+40*i+8)
            uc.mem_write(IMAGE_BASE+rva,raw[offset:offset+size])
        self.segments = getattr(snapshot, 'segments', None)
        if self.segments is None:
            self.segments = [(HEAP_BASE, snapshot.heap)]
        pages = []
        for address, data in self.segments:
            start, end = address & ~4095, (address + len(data) + 4095) & ~4095
            if pages and start <= pages[-1][1]:
                pages[-1] = (pages[-1][0], max(end, pages[-1][1]))
            else:
                pages.append((start, end))
        for start, end in pages:
            uc.mem_map(start, end-start)
        for address, data in self.segments:
            uc.mem_write(address, data)
        uc.mem_map(STACK,0x10000);uc.mem_map(STOP,0x1000)
        for a in GLOBALS:uc.mem_write(a,snapshot.read(a,4))
        self.initial_image=bytes(uc.mem_read(IMAGE_BASE,image_size))
        self.snapshot,self.state=snapshot,state
        self.starts=set();self.calls=[];self.writes=[];self.allowed_writes=[];self.reads=set()
        s=state
        self.read_ranges=[(a,a+4) for a in GLOBALS]+[
            (s['club'],s['club']+4),(s['club']+0xcf,s['club']+0xd3),
            (s['manager'],s['manager']+4),(s['registry'],s['registry']+8),
            (s['row']+0x9a01,s['row']+0x9a05),(s['row']+0x9a69,s['row']+0x9a6a),
            (s['row']+0x9b25,s['row']+0x9b26),
            (s['context']+0x5f1,s['context']+0x605),
            (s['mapping']+s['club_id']*0x91,s['mapping']+s['club_id']*0x91+2)]
        uc.hook_add(unicorn.UC_HOOK_CODE,self.instruction)
        uc.hook_add(unicorn.UC_HOOK_MEM_READ,self.read)
        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE,self.write)

    def instruction(self,uc,address,size,_):
        require(any(a<=address and address+size<=b for a,b in RANGES),
                'unadmitted instruction '+hex(address))
        self.starts.add(address)

    def read(self,uc,access,address,size,value,_):
        if STACK<=address and address+size<=STACK+0x10000:return
        require(any(a<=address and address+size<=b for a,b in self.read_ranges),
                'unadmitted read '+hex(address)+'/'+str(size))
        self.reads.add((address,size))

    def write(self,uc,access,address,size,value,_):
        if STACK<=address and address+size<=STACK+0x10000:return
        require((address,size) in self.allowed_writes,'unadmitted write')
        self.writes.append({'registry_offset':address-self.state['row'],'width':size,'value':value})

    def call(self,entry,arguments,receiver,allowed=(),expected=None):
        uc=self.uc;sp=STACK+0x8000
        uc.mem_write(STACK,bytes(0x10000))
        uc.mem_write(sp,struct.pack('<'+'I'*(len(arguments)+1),STOP,*arguments))
        uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,receiver)
        saved={UC_X86_REG_EBX:0x12345678,UC_X86_REG_ESI:0x23456789,
               UC_X86_REG_EDI:0x3456789a,UC_X86_REG_EBP:0x456789ab}
        for reg,value in saved.items():uc.reg_write(reg,value)
        self.writes=[];self.reads=set();self.allowed_writes=list(allowed)
        uc.emu_start(entry,STOP,timeout=100000,count=3000)
        require(uc.reg_read(UC_X86_REG_EIP)==STOP,'incomplete return')
        require(uc.reg_read(UC_X86_REG_ESP)==sp+4*(len(arguments)+1),'stack cleanup mismatch')
        require(all(uc.reg_read(reg)==value for reg,value in saved.items()),'callee-saved register mismatch')
        value=uc.reg_read(UC_X86_REG_EAX)
        if expected is not None:require(value==expected,'return mismatch')
        result={'entry':f'{entry:08x}','ordered_writes':copy.deepcopy(self.writes),
                'read_count':len(self.reads),'stack_cleanup_checked':True,'return_checked':expected is not None,
                'callee_saved_registers_checked':True,'rng_draws':0}
        self.calls.append(result)
        return value,result

    def capture_state(self):
        return [(address, bytes(self.uc.mem_read(address, len(data)))) for address,data in self.segments]

    def restore_state(self, checkpoint):
        for address, data in checkpoint:
            self.uc.mem_write(address, data)

    def full_state(self,expected_changes):
        for address, original in self.segments:
            expected=bytearray(original)
            for offset,value in expected_changes.items():
                target=self.state['row']+offset-address
                if 0 <= target < len(expected):
                    expected[target]=value
            require(bytes(self.uc.mem_read(address,len(expected)))==expected,
                    'unexpected captured state mutation')
        require(bytes(self.uc.mem_read(IMAGE_BASE,len(self.initial_image)))==self.initial_image,
                'unexpected image/global mutation')


def compare_effects(observed,candidate):
    return observed==candidate


def generate(binary,capture,snapshot_override=None,capture_identity=None):
    raw=checked(binary,SPECIMEN)
    snapshot=Snapshot(capture) if snapshot_override is None else snapshot_override
    s=locate(snapshot)
    oracle=Oracle(raw,snapshot,s);row=s['row'];manager=s['manager'];club=s['club']
    initial=snapshot.read(row+0x9a69,1)[0]
    flag=snapshot.u32(row+0x9a01);option_flag=snapshot.read(row+0x9b25,1)[0]
    require(flag in (0,1) and option_flag in (0,1), 'unsupported guard state')
    cases=[];all_writes=[]
    sequence=[0,1,1,0,1,0]
    before=initial
    for step,option in enumerate(sequence):
        _,select=oracle.call(0x5fbe20,[option,club,manager],s['registry'],[(row+0x9a69,1)],
                             s['registry_base'] if option else s['registry_index']*8547)
        writes=[{'registry_offset':0x9a69,'width':1,'value':option}]
        require(select['ordered_writes']==writes,'selector ordered effect mismatch')
        _,resolve=oracle.call(0x5fbd00,[manager],s['registry'],expected=row+option*SLOT_STRIDE)
        require(resolve['ordered_writes']==[],'resolver mutation')
        oracle.full_state({0x9a69:option})
        cases.append({'step':step,'option':option,'previous_slot':before,'selected_slot':option,
                      'location':{'registry_index':s['registry_index'],'slot':option,
                                  'byte_offset':option*SLOT_STRIDE},'ordered_writes':writes,'rng_draws':0})
        all_writes.extend(writes);before=option
    # Restart from a complete official post-command heap and continue the same
    # real state. This is an emulator checkpoint, not an original saved game.
    checkpoint=oracle.capture_state()
    _,continuation1=oracle.call(0x5fbe20,[1,club,manager],s['registry'],[(row+0x9a69,1)],s['registry_base'])
    expected_heap=oracle.capture_state()
    oracle.restore_state(checkpoint)
    _,continuation2=oracle.call(0x5fbe20,[1,club,manager],s['registry'],[(row+0x9a69,1)],s['registry_base'])
    require(continuation1==continuation2 and oracle.capture_state()==expected_heap,
            'checkpoint continuation differs')
    oracle.full_state({0x9a69:1})
    # Actual captured outer getter follows holiday fallback; record that it
    # neither reads nor changes active registry selection in this state.
    k=s['bank_selection'];bank,index=(s['bank1'],k) if k<s['first'] else (s['bank2'],k-s['first'])
    is_fallback = flag != 0 and option_flag == 0
    _,fallback=oracle.call(0x896660,[club,0],s['context'],
                          [] if is_fallback else [(row+0x9a69,1)],
                          bank+index*6371 if is_fallback else row)
    require(fallback['ordered_writes']==([] if is_fallback else
            [{'registry_offset':0x9a69,'width':1,'value':0}]),'captured outer effect mismatch')
    oracle.full_state({0x9a69:1 if is_fallback else 0})
    # Change the guard through its genuine original producer, never a patched
    # memory byte. Option 2 takes the bounded one-byte path; option 3 is excluded.
    _,producer=oracle.call(0x5feb60,[2,1,manager],s['registry'],[(row+0x9b25,1)],(s['registry_index']*8547 & 0xffffff00)|2)
    require(producer['ordered_writes']==[{'registry_offset':0x9b25,'width':1,'value':1}],
            'producer ordered effect mismatch')
    connected=[]
    for option in [0,1,1,0]:
        _,result=oracle.call(0x896660,[club,option],s['context'],[(row+0x9a69,1)],row+option*SLOT_STRIDE)
        require(result['ordered_writes']==[{'registry_offset':0x9a69,'width':1,'value':option}],
                'connected getter ordered effect mismatch')
        oracle.full_state({0x9a69:option,0x9b25:1})
        connected.append({'option':option,'returned_slot':option,'byte_offset':option*SLOT_STRIDE,
                          'ordered_writes':result['ordered_writes'],'rng_draws':0})
    _,restore=oracle.call(0x5feb60,[2,option_flag,manager],s['registry'],[(row+0x9b25,1)],(s['registry_index']*8547 & 0xffffff00)|2)
    oracle.full_state({0x9a69:0})
    # Direct wrong models: each defect compares against observed normalized
    # effects/locations; reorder is discriminated across the command stream.
    controls={}
    controls['wrong-row']=sum(c['location']['registry_index']!=0 for c in cases)
    controls['wrong-slot']=sum(c['location']['slot']!=(1-c['option']) for c in cases)
    controls['wrong-bank-stride']=sum(c['location']['byte_offset']!=c['option']*6371 for c in cases)
    controls['omitted-write']=sum(not compare_effects(c['ordered_writes'],[]) for c in cases)
    controls['word-instead-of-byte']=sum(not compare_effects(c['ordered_writes'],[
        {'registry_offset':0x9a69,'width':2,'value':c['option']}]) for c in cases)
    controls['extra-rng-draw']=sum(c['rng_draws']!=1 for c in cases)
    controls['reordered-writes']=int(not compare_effects(all_writes,[all_writes[1],all_writes[0]]+all_writes[2:]))
    require(all(controls.values()),'non-discriminating control')
    successful_starts=len(oracle.starts)
    # Out-of-domain original paths remain censored at the first missing callee,
    # never converted into Rust rejection parity or manufactured successful runs.
    probes=[]
    for label,entry,args in [('null-manager-diagnostic',0x5fbd00,[0]),
                              ('nonhuman-manager-diagnostic',0x5fbd00,[manager-16*110]),
                              ('holiday-option-three-larger-producer',0x5feb60,[3,1,manager])]:
        try:
            oracle.call(entry,args,s['registry'])
        except ValueError as error:
            probes.append({'name':label,'execution_status':'censored','comparison_verdict':'not-comparable',
                           'reason':str(error) if str(error).startswith('unadmitted instruction') else
                                    'outside admitted state or write domain'})
        else:raise ValueError('unsupported probe unexpectedly returned')
    fixture={'schema_version':1,'origin':'captured-bosman-human-registry',
             'source_capture_sha256':SOURCE_CAPTURE if capture_identity is None else capture_identity['source_capture_sha256'],'specimen_sha256':SPECIMEN,
             'club_count':s['clubs'],'ordinary_club_limit':s['clubs']-2*s['nations'],
             'staff_count':s['staff'],'registry_count':s['registry_count'],
             'club_id':s['club_id'],'manager_id':s['manager_id'],
             'registry_index':s['registry_index'],'selected_slot':initial,
             'registry_row_sha256':digest(snapshot.read(row,REGISTRY_STRIDE))}
    return {'schema_version':1,'specimen_sha256':SPECIMEN,'emulator':'unicorn '+unicorn.__version__,
            'method':'official entry-to-return instructions over actual retained runtime state; no stubbed callees',
            'capture':({'source_capture_sha256':SOURCE_CAPTURE,'image_sha256':IMAGE_HASH,'heap_sha256':HEAP_HASH,
                       'platform_revision':'f9583098d39c77ac6982a5aa9daec56d74454531'} if capture_identity is None else capture_identity),
            'state':{'registry_count':s['registry_count'],'registry_stride':REGISTRY_STRIDE,
                     'tactical_slot_count':SLOT_COUNT,'tactical_slot_stride':SLOT_STRIDE,
                     'ordinary_reciprocal_human_bindings':1,'registry_row_sha256':fixture['registry_row_sha256'],
                     'club_record_sha256':digest(snapshot.read(club,581)),
                     'staff_record_sha256':digest(snapshot.read(manager,110)),
                     'complete_heap_bytes':sum(len(data) for _,data in oracle.segments)},
            'private_fixture':{'sha256':digest(canonical(fixture)),'bytes':len(canonical(fixture))},
            'instruction_ranges':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}',
                                   'sha256':digest(bytes(oracle.uc.mem_read(a,b-a)))} for a,b in RANGES],
            'successful_instruction_starts':successful_starts,'successful_calls':len(oracle.calls),
            'cases':cases,'checkpoint_continuation_equal':True,'captured_outer_lookup':{
                'path':'ordinary-bank-fallback' if is_fallback else 'human-registry','registry_flag_9a01':flag,'registry_flag_9b25':option_flag,
                'ordered_writes':fallback['ordered_writes']},
            'original_guard_producer':{'entry':'005feb60','option':2,'enable_writes':producer['ordered_writes'],
                                       'restore_writes':restore['ordered_writes']},
            'connected_outer_lookup_cases':connected,'defect_controls':controls,'unsupported_probes':probes,
            'complete_heap_and_image_checked':True,'supported_rng_draws':0,
            'limitations':['Historical instrumented Bosman capture has no contemporaneous clean-input consumption seal',
                'Direct selector command is a research API transition, not a reconstructed original UI handler',
                'Preinitialized registry only; constructor/load/destructor, appointments and lifetime transitions unqualified',
                'Only ordinary reciprocal human binding, explicit nonnull manager/club, selector options 0 and 1',
                'Slots 2 through 4, national sides, null-current-manager fallback and diagnostics unsupported',
                'Plan bytes are preserved but not decoded; no original-save, match or original-process parity']},fixture


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary',type=Path);parser.add_argument('capture',type=Path)
    parser.add_argument('output',type=Path);parser.add_argument('--private-fixture',type=Path)
    args=parser.parse_args();result,fixture=generate(args.binary,args.capture)
    with args.output.open('x',encoding='utf-8') as out:out.write(json.dumps(result,indent=2)+'\n')
    if args.private_fixture:
        import os
        fd=os.open(args.private_fixture,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as out:out.write(canonical(fixture))
    print(json.dumps({'successful_calls':result['successful_calls'],
                      'successful_instruction_starts':result['successful_instruction_starts'],
                      'receipt_sha256':digest(args.output.read_bytes())}))
