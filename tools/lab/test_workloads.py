"""Lightweight adapter controls; no production binary, emulator or Bosman runs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('workloads',Path(__file__).with_name('workloads.py'))
w=importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)

class Workloads(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.config={'python':sys.executable}
        self.manifest=w.build_profile('synthetic',self.config,ROOT,'unit')
        self.job=self.manifest['jobs'][0]

    def tearDown(self):
        self.temp.cleanup()

    def test_frozen_pins_and_configuration_fail_closed(self):
        w.validate(self.manifest,ROOT,self.config)
        w.validate_job(self.manifest,self.job,ROOT,self.config)
        with self.assertRaisesRegex(ValueError,'configuration changed'):
            w.validate(self.manifest,ROOT,{**self.config,'extra':'changed'})
        bad=copy.deepcopy(self.manifest)
        bad['pins'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):
            w.validate(bad,ROOT,self.config)

    def test_unapproved_commands_and_widened_parameters_reject(self):
        for changes in [{'template_id':'shell'},{'parameters':{'argv':['echo']}},
                        {'parameters':{'steps':True}},{'parameters':{'steps':1001}},
                        {'parameters':{'mode':'unknown'}}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                w.validate_job(self.manifest,{**self.job,**changes},ROOT,self.config)

    def test_unpinned_tool_is_rejected(self):
        bad=copy.deepcopy(self.job)
        bad['pins']=[]
        with self.assertRaisesRegex(ValueError,'not pinned'):
            w.validate_job(self.manifest,bad,ROOT,self.config)

    def test_synthetic_complete_endpoint_and_failure_are_distinct(self):
        for mode,status in [('normal','succeeded'),('fail','failed')]:
            attempt=self.root/mode
            attempt.mkdir()
            job={**self.job,'parameters':{'steps':2,'delay_ms':0,'mode':mode}}
            prepared=w.prepare(self.manifest,job,attempt,ROOT,self.config)
            code=subprocess.call(prepared['argv'],cwd=prepared['cwd'],env=prepared['env'])
            result=w.result(self.manifest,job,attempt,code)
            self.assertEqual(result['execution_status'],status)
            self.assertEqual(json.loads((attempt/'progress.json').read_text())['sequence'],
                             1000000 if mode=='normal' else 2)
            self.assertNotIn('shell',prepared)
            self.assertEqual(prepared['argv'][1],'-I')

    def test_missing_or_mismatched_endpoint_cannot_pass(self):
        self.assertEqual(w.result(self.manifest,self.job,self.root,0)['execution_status'],'infrastructure_failed')
        (self.root/'workload-result.json').write_text(json.dumps(
            {'execution_status':'succeeded','comparison_verdict':'equal','details':{},
             'template_id':'other'}))
        self.assertEqual(w.result(self.manifest,self.job,self.root,0)['comparison_verdict'],'not-comparable')

    def test_bosman_widening_is_rejected_before_launch(self):
        request={'backend':{'kind':'bosman-native'},
                 'expected_stop_condition':'classic-same-save-normal-again-14-days-equal',
                 'commands':[{'kind':'bosman-classic-same-save-v1','parameters':
                    dict(mode='classic',days=30,jobs=2,runs=['normal','again'],seed=1,
                         fixed_clock=True,expected_save_relation='byte-identical')}]}
        request_path=self.root/'request.json'
        request_path.write_text(json.dumps(request))
        config={'bosman_request':str(request_path)}
        with patch.object(w,'_files',return_value=[]),self.assertRaisesRegex(ValueError,'widening'):
            w.validate_job(self.manifest,{'template_id':'bosman-same-save-v1','parameters':{}},ROOT,config)

    def test_research_novel_inverse_set_question_and_controls(self):
        # Tiny structural specimen, with dimensions/strides identical to frozen
        # input schema; fixture pins patched only inside this parser unit test.
        image=bytearray(0xA00000)
        heap=bytearray(0x10000)
        base=0x70000000
        cb,sb,pb=base,base+0x1000,base+0x4000
        def put(address,value):
            raw,start=(image,address-0x400000) if address<base else (heap,address-base)
            struct.pack_into('<I',raw,start,value)
        for address,value in [(0xae235c,3),(0xae2350,1),(0xae2364,18),(0xae236c,2),
                              (0xae23b4,cb),(0xae23bc,sb),(0xae23c4,pb)]:
            put(address,value)
        for index in range(18):
            put(sb+110*index,index)
        put(cb,0)
        put(cb+0xcf,sb+2*110)
        put(sb+2*110+0x39,cb)
        put(sb+0x39,cb)
        put(sb+0x61,pb)
        put(sb+110+0x39,cb+581)
        put(sb+110+0x61,pb+70)
        # Hidden inverse association with valid player link is the novel
        # discriminator; it is absent from all fifty list slots.
        put(sb+3*110+0x39,cb)
        put(sb+3*110+0x61,pb+70)
        put(pb,0)
        put(pb+70,1)
        for slot in range(50):
            put(cb+0xd7+4*slot,sb if slot<43 else sb+110 if slot<48 else 0)
        capture=self.root/'capture'
        capture.mkdir()
        (capture/'image.bin').write_bytes(image)
        (capture/'heap.bin').write_bytes(heap)
        with patch.object(w,'IMAGE_SHA',w.sha(capture/'image.bin')),patch.object(w,'HEAP_SHA',w.sha(capture/'heap.bin')):
            observed=w._research({'retained_capture':str(capture)})
        self.assertEqual(observed['set_comparison']['inverse_only'],1)
        self.assertFalse(observed['hypotheses']['H1_exact_candidate_set_equality'])
        self.assertEqual(len(observed['controls']),6)
        self.assertTrue(all(observed['controls'].values()))
        self.assertEqual(observed['counts']['slots'],50)
        self.assertEqual(observed['counts']['foreign_club'],5)
        self.assertEqual(observed['counts']['invalid_staff'],2)
        self.assertEqual(observed['production_admission'],'none')

if __name__=='__main__':
    unittest.main()

