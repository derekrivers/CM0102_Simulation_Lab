#!/usr/bin/env python3
"""Small synthetic R9b controls. All attempt artifacts retained privately."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import unittest
import uuid
import pc_r9b_file_use as use

PROGRAM = r'''
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>
int main(int argc,char **argv) {
 if(argc!=4)return 2;
 if(getenv("CONTROL_REEXEC") && !getenv("RECOMP_STACK_SET")) {
  setenv("RECOMP_STACK_SET","1",1);execv(argv[0],argv);return 11;
 }
 if(getenv("CONTROL_CLONE")) { syscall(SYS_clone,0,0,0,0,0);return 12; }
 if(getenv("CONTROL_FORK")) { syscall(SYS_fork);return 13; }
 if(getenv("CONTROL_CLONE3")) { syscall(SYS_clone3,0,0);return 14; }
 if(getenv("CONTROL_VFORK")) { syscall(SYS_vfork);return 15; }
 if(getenv("CONTROL_X32")) { syscall(0x40000000|SYS_getpid);return 16; }
 sigset_t before,after;sigprocmask(SIG_SETMASK,NULL,&before);
 char b[8]={0};int a=open(argv[1],O_RDONLY);if(a<0)return 3;
 errno=EDOM;if(read(a,b,3)!=3 || errno!=EDOM)return 4;
 sigprocmask(SIG_SETMASK,NULL,&after);
 for(int i=1;i<NSIG;i++)if(sigismember(&before,i)!=sigismember(&after,i))return 20;
 for(int i=0;i<100000;i++)if(pread(a,b,1,0)!=1)return 5;
 close(a);
 FILE *f=fopen(argv[1],"rb");if(!f)return 6;
 if(fread(b,2,2,f)!=1 || b[2]!='C')return 7;
 fclose(f);
 a=open(argv[2],O_RDONLY);if(a<0)return 8;
 void *m=mmap(NULL,3,PROT_READ,MAP_PRIVATE,a,0);if(m==MAP_FAILED)return 9;
 munmap(m,3);close(a);
 a=open(argv[3],O_RDONLY);if(a<0)return 10;close(a);
 errno=0;if(open("/no-such-pc-r9b-control",O_RDONLY)!=-1 || errno!=ENOENT)return 17;
 errno=0;if(open("/second-no-such-pc-r9b-control",O_RDONLY)!=-1 || errno!=ENOENT)return 18;
 return 0;
}
'''


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path('/home/derek/.local/share/cm0102-simulation-lab/evidence') / (
            'pc-r9b-controls-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
        cls.root.mkdir(mode=0o700)
        (cls.root/'program.c').write_text(PROGRAM)
        commands = [
            ['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O0',
             str(cls.root/'program.c'), '-o', str(cls.root/'control')],
            ['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
             '-shared', '-fPIC', str(use.observer_source()), '-o', str(cls.root/'observer.so'),
             '-ldl', '-pthread']]
        use.r5.write(cls.root/'commands.json', commands)
        for i, command in enumerate(commands):
            result = subprocess.run(command, capture_output=True, timeout=30)
            (cls.root/f'compile-{i}.stdout').write_bytes(result.stdout)
            (cls.root/f'compile-{i}.stderr').write_bytes(result.stderr)
            if result.returncode:
                raise AssertionError('synthetic control compile failed; artifacts retained')
        cls.members = {}
        for name in ('read-file', 'mapped-file', 'open-file'):
            p = cls.root/name
            p.write_bytes(b'ABC')
            s = p.stat()
            cls.members[str(p)] = {'dev': s.st_dev, 'ino': s.st_ino, **use.r5.identity(p)}
        (cls.root/'linked').symlink_to(cls.root/'open-file')
        cls.trace = cls.root/'normal.tsv'
        cls.invoke('normal')
        cls.summary = use.parse_trace(cls.trace, cls.members)
        use.r5.write(cls.root/'control-summary-private.json', cls.summary)

    @classmethod
    def invoke(cls, name, **extra):
        env = {'PATH': '/usr/bin:/bin', 'LD_PRELOAD': str(cls.root/'observer.so'),
            'PC_R9B_TRACE': str(cls.root/(name+'.tsv')), 'PC_R9B_CLEAN_ROOT': str(cls.root), **extra}
        args = [str(cls.root/'control'), str(cls.root/'read-file'),
                str(cls.root/'mapped-file'), str(cls.root/'linked')]
        use.r5.write(cls.root/(name+'-command.json'), {'argv': args, 'environment': env})
        result = subprocess.run(args, env=env, capture_output=True, timeout=20)
        (cls.root/(name+'.stdout')).write_bytes(result.stdout)
        (cls.root/(name+'.stderr')).write_bytes(result.stderr)
        use.r5.write(cls.root/(name+'-result.json'), {'returncode': result.returncode})
        return result.returncode

    def modified(self, text, name):
        p = self.root/(name+'.tsv')
        p.write_text(text)
        return p

    def test_identity_volume_items_and_masks(self):
        s = self.summary
        self.assertEqual(s['successful_open_manifest_files'], 3)
        self.assertEqual(s['positive_read_manifest_files'], 1)
        self.assertEqual(s['mapped_manifest_files'], 1)
        self.assertEqual(s['failed_operations'], 2)
        self.assertEqual(s['operations']['pread'], 100000)
        self.assertLess(self.trace.stat().st_size, 20000)
        item = [r for r in s['rows'] if r['operation'] == 'fread'][0]
        self.assertEqual(item['complete_fread_items'], 1)
        self.assertEqual(item['delivered_api_bytes_lower_bound'], 2)
        self.assertEqual(item['short_multi_byte_fread_calls'], 1)
        self.assertFalse(s['api_totals_are_unique_bytes'])
        self.assertEqual(s['absolute_supplied_symlinks_at_analysis'], 1)
        self.assertNotIn(b'ABC', self.trace.read_bytes())

    def test_concurrent_fd_reuse_cannot_enter_qualified_interval(self):
        # Every host creation route is a raw syscall, bypassing libc wrappers.
        for key in ('CLONE', 'CLONE3', 'FORK', 'VFORK', 'X32'):
            name = key.lower()
            self.assertEqual(self.invoke(name, **{'CONTROL_'+key: '1'}), -signal.SIGSYS)
            with self.assertRaises(ValueError):
                use.parse_trace(self.root/(name+'.tsv'), self.members)

    def test_reexec_exclusive_lifecycle(self):
        self.assertEqual(self.invoke('ungated', CONTROL_REEXEC='1'), 124)
        with self.assertRaises(ValueError):
            use.parse_trace(self.root/'ungated.tsv', self.members)
        self.assertEqual(self.invoke('gated', CONTROL_REEXEC='1',
                         PC_R9B_WAIT_FOR_STACK_REEXEC='1'), 0)
        self.assertEqual(use.parse_trace(self.root/'gated.tsv', self.members)['operations']['pread'], 100000)

    def test_wrong_identity_is_failure(self):
        wrong = copy.deepcopy(self.members)
        wrong[str(self.root/'read-file')]['ino'] += 1
        with self.assertRaises(ValueError):
            use.parse_trace(self.trace, wrong)

    def test_missing_truncated_overflow_and_lost_detail(self):
        raw = self.trace.read_text()
        candidates = {'missing-footer': raw.rsplit('PCR9BDONE', 1)[0],
            'missing-policy': raw.replace('POLICY\tx86_64-tsync-single-task-no-clone-v1\n', ''),
            'truncated': raw[:-1],
            'overflow': raw.rsplit('\t0\n', 1)[0]+'\t1\n'}
        lines = raw.splitlines()
        candidates['lost-detail'] = '\n'.join(l for l in lines if not l.startswith('A\t'))+'\n'
        candidates['duplicate-row'] = '\n'.join(lines[:3]+[lines[2]]+lines[3:])+'\n'
        for name, value in candidates.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                use.parse_trace(self.modified(value, name), self.members)

    def helper_library(self, name, source):
        p = self.root/(name+'.c')
        p.write_text(source)
        command = ['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O0',
            '-shared', '-fPIC', str(p), '-o', str(self.root/(name+'.so')), '-ldl', '-pthread']
        use.r5.write(self.root/(name+'-build.json'), command)
        result = subprocess.run(command, capture_output=True, timeout=30)
        (self.root/(name+'-build.stderr')).write_bytes(result.stderr)
        self.assertEqual(result.returncode, 0)
        return self.root/(name+'.so')

    def test_preexisting_task_census_fails(self):
        helper = self.helper_library('preexisting-thread', r'''
#define _GNU_SOURCE
#include <pthread.h>
#include <unistd.h>
static void *worker(void *arg){(void)arg;for(;;)pause();return 0;}
__attribute__((constructor)) static void start(void){pthread_t thread;if(pthread_create(&thread,0,worker,0))_exit(44);}
''')
        # ELF initialization runs this later preload before the observer.
        preload = str(self.root/'observer.so')+':'+str(helper)
        self.assertEqual(self.invoke('preexisting', LD_PRELOAD=preload), 116)
        with self.assertRaises(ValueError):
            use.parse_trace(self.root/'preexisting.tsv', self.members)

    def test_nested_api_counts_are_separate(self):
        helper = self.helper_library('nested', r'''
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
FILE *fopen(const char *path,const char *mode){
 FILE *(*next)(const char *,const char *);*(void **)(&next)=dlsym(RTLD_NEXT,"fopen");
 int fd=open(path,O_RDONLY);if(fd>=0){char c;read(fd,&c,1);close(fd);}return next(path,mode);
}
''')
        preload = str(self.root/'observer.so')+':'+str(helper)
        self.assertEqual(self.invoke('nested', LD_PRELOAD=preload), 0)
        s = use.parse_trace(self.root/'nested.tsv', self.members)
        read = [row for row in s['rows'] if row['operation'] == 'read'][0]
        self.assertEqual(read['calls'], 2)
        self.assertEqual(read['nested_calls'], 1)
        self.assertEqual(read['delivered_api_bytes_lower_bound'], 4)
        self.assertEqual(s['operations']['fread'], 1)

    def test_all_frozen_observer_capacity_failures(self):
        original = use.observer_source().read_text()
        variants = {
            'row-saturation': original.replace('#define ROW_CAP 2048u', '#define ROW_CAP 1u'),
            'abnormal-saturation': original.replace('#define ABNORMAL_CAP 1024u', '#define ABNORMAL_CAP 1u'),
            'output-saturation': original.replace('#define OUTPUT_CAP (16u*1024u*1024u)', '#define OUTPUT_CAP 1024u'),
            'counter-overflow': original.replace('static uint64_t events, errors,', 'static uint64_t events=UINT64_MAX, errors,')}
        for name, source in variants.items():
            with self.subTest(name=name):
                p = self.root/(name+'.c')
                p.write_text(source)
                command = ['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-O2', '-shared', '-fPIC', str(p), '-o', str(self.root/(name+'.so')), '-ldl', '-pthread']
                use.r5.write(self.root/(name+'-build.json'), command)
                result = subprocess.run(command, capture_output=True, timeout=30)
                (self.root/(name+'-build.stderr')).write_bytes(result.stderr)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(self.invoke(name, LD_PRELOAD=str(self.root/(name+'.so'))), 0)
                with self.assertRaises(ValueError):
                    use.parse_trace(self.root/(name+'.tsv'), self.members)

    def test_positive_error_delivery_is_not_discarded(self):
        lines = self.trace.read_text().splitlines()
        for i, line in enumerate(lines):
            fields = line.split('\t')
            if fields[0] == 'R' and fields[2] == 'fread':
                fields[3] = '0'
                fields[4] = '5'
                lines[i] = '\t'.join(fields)
                index = fields[1]
                target, given = fields[-2:]
                footer = lines.pop().split('\t')
                # Insert detail at an unused sequence with that row's delivery.
                prior = next(j for j, x in enumerate(lines) if x.startswith('A\t'))
                lines.insert(prior, '\t'.join(['A', '100005', index, '3', '4', '2', '5', target, given]))
                footer[3] = str(int(footer[3])+1)
                lines.append('\t'.join(footer))
                break
        summary = use.parse_trace(self.modified('\n'.join(lines)+'\n', 'positive-error'), self.members)
        self.assertEqual(summary['positive_read_manifest_files'], 1)
        self.assertEqual(summary['failed_operations'], 3)

    def test_noninterference_requires_every_arm(self):
        records = [{'save': {'sha256': use.SAVE}, 'capture_complete': True,
                    'capture': {'sha256': use.CAPTURE}} for _ in range(4)]
        self.assertEqual(use.exact_noninterference(records, True), (True, True))
        records[2]['save']['sha256'] = 'bad'
        self.assertEqual(use.exact_noninterference(records, True), (False, True))
        records[2]['capture']['sha256'] = 'bad'
        self.assertEqual(use.exact_noninterference(records, True), (False, False))
        self.assertEqual(use.exact_noninterference(records, False), (False, False))


if __name__ == '__main__':
    os.umask(0o077)
    unittest.main()