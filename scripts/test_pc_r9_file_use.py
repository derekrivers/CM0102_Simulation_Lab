#!/usr/bin/env python3
"""Redistributable controls for affirmative file-use observation."""
import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import pc_r9_file_use as use

PROGRAM = r"""
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/mman.h>
#include <unistd.h>
int main(int argc, char **argv) {
  if (argc != 4) return 2;
  char b[4];
  int a = open(argv[1], O_RDONLY);
  if (a < 0) return 3;
  errno = EDOM;
  if (read(a, b, 4) != 4 || errno != EDOM) return 4;
  if (pread(a, b, 4, 0) != 4) return 5;
  close(a);
  FILE *f = fopen(argv[1], "rb");
  if (!f || fread(b, 1, 4, f) != 4) return 6;
  fclose(f);
  a = open(argv[2], O_RDONLY);
  if (a < 0) return 7;
  void *m = mmap(0, 4, PROT_READ, MAP_PRIVATE, a, 0);
  if (m == MAP_FAILED) return 8;
  munmap(m, 4); close(a);
  a = open(argv[3], O_RDONLY);
  if (a < 0) return 9;
  close(a);
  errno = 0;
  if (open("/no-such-pc-r9-control", O_RDONLY) != -1 || errno != ENOENT) return 10;
  return 0;
}
"""


class FileUseControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root/'program.c').write_text(PROGRAM)
        subprocess.run(['/usr/bin/cc', '-std=c11', '-D_GNU_SOURCE', '-O0',
            str(cls.root/'program.c'), '-o', str(cls.root/'control')], check=True)
        subprocess.run(['/usr/bin/cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
            '-shared', '-fPIC', str(use.observer_source()), '-o', str(cls.root/'observer.so'),
            '-ldl', '-pthread'], check=True)
        cls.members = {}
        for name in ['read-file', 'mapped-file', 'open-file']:
            p = cls.root/name
            p.write_bytes(b'PRIVATE_CONTROL_CONTENT')
            s = p.stat()
            cls.members[str(p)] = {'dev': s.st_dev, 'ino': s.st_ino,
                **use.r5.identity(p)}
        (cls.root/'linked').symlink_to(cls.root/'open-file')
        cls.trace = cls.root/'trace.tsv'
        env = dict(os.environ, LD_PRELOAD=str(cls.root/'observer.so'), PC_R9_TRACE=str(cls.trace))
        subprocess.run([str(cls.root/'control'), str(cls.root/'read-file'),
            str(cls.root/'mapped-file'), str(cls.root/'linked')], env=env, check=True)
        cls.summary = use.parse_trace(cls.trace, cls.members)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def modified(self, text):
        p = self.root/'modified.tsv'
        p.write_text(text)
        return p

    def test_actual_open_read_mapping_and_fd_reuse(self):
        s = self.summary
        self.assertEqual(s['successful_open_manifest_files'], 3)
        self.assertEqual(s['positive_read_manifest_files'], 1)
        self.assertEqual(s['mapped_manifest_files'], 1)
        self.assertEqual(s['failed_operations'], 1)
        self.assertEqual(s['absolute_supplied_symlinks_at_analysis'], 1)
        self.assertFalse(s['mapped_pages_read_proven'])
        self.assertFalse(s['semantic_use_of_every_byte_proven'])
        self.assertNotIn(b'PRIVATE_CONTROL_CONTENT', self.trace.read_bytes())

    def test_wrong_descriptor_identity_never_binds(self):
        wrong = copy.deepcopy(self.members)
        wrong[str(self.root/'read-file')]['ino'] += 1
        s = use.parse_trace(self.trace, wrong)
        self.assertEqual(s['positive_read_manifest_files'], 0)
        self.assertGreater(s['identity_mismatches'], 0)

    def test_incomplete_trace_fails(self):
        with self.assertRaises(ValueError):
            use.parse_trace(self.modified(self.trace.read_text().rsplit('PCR9DONE', 1)[0]), self.members)

    def test_dropped_records_fail(self):
        content = self.trace.read_text().splitlines()
        content[-1] = content[-1].rsplit('\t', 2)[0]+'\t1\t0'
        with self.assertRaises(ValueError):
            use.parse_trace(self.modified('\n'.join(content)+'\n'), self.members)

    def test_sequence_and_footer_count_fail(self):
        content = self.trace.read_text().splitlines()
        content[1] = '999'+content[1][content[1].index('\t'):]
        with self.assertRaises(ValueError):
            use.parse_trace(self.modified('\n'.join(content)+'\n'), self.members)
        content = self.trace.read_text().splitlines()
        content[-1] = 'PCR9DONE\t999\t0\t0'
        with self.assertRaises(ValueError):
            use.parse_trace(self.modified('\n'.join(content)+'\n'), self.members)

    def test_noninterference_mismatches_never_pass(self):
        records = [{'save': {'sha256': use.SAVE}, 'capture_complete': True,
                    'capture': {'sha256': use.CAPTURE}} for _ in range(4)]
        self.assertEqual(use.exact_noninterference(records, True), (True, True))
        changed = copy.deepcopy(records)
        changed[2]['save']['sha256'] = '0'*64
        self.assertEqual(use.exact_noninterference(changed, True), (False, True))
        changed = copy.deepcopy(records)
        changed[3]['capture']['sha256'] = '0'*64
        self.assertEqual(use.exact_noninterference(changed, True), (True, False))
        self.assertEqual(use.exact_noninterference(records, False), (False, False))
        self.assertEqual(use.exact_noninterference(records[:-1], True), (False, False))

    def test_overlong_supplied_path_invalidates_trace(self):
        p = self.root/'overlong.tsv'
        env = dict(os.environ, LD_PRELOAD=str(self.root/'observer.so'), PC_R9_TRACE=str(p))
        result = subprocess.run([str(self.root/'control'), '/'+'x'*5000, 'b', 'c'], env=env)
        self.assertEqual(result.returncode, 3)
        with self.assertRaises(ValueError):
            use.parse_trace(p, self.members)

    def test_trace_reuse_fails_without_overwrite(self):
        old = self.trace.read_bytes()
        env = dict(os.environ, LD_PRELOAD=str(self.root/'observer.so'), PC_R9_TRACE=str(self.trace))
        result = subprocess.run([str(self.root/'control'), 'a', 'b', 'c'], env=env)
        self.assertEqual(result.returncode, 124)
        self.assertEqual(old, self.trace.read_bytes())


if __name__ == '__main__':
    unittest.main()
