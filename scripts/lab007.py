"""Frozen retained two-member, twenty-slot experiment; lab admission owns execution.

Raw mapped bytes and CPU contexts are private evidence. No synthetic retained
state, widened membership, diagnostic probe, or original process is introduced.
"""
import copy
import ctypes
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

# Isolated Python entry points deliberately do not inherit cwd on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unicorn
import unicorn.x86_const as registers
import capstone
from unicorn.x86_const import (UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_ECX,
                              UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
from qualify_human_registry import STOP
from lab007_cases import definition
from qualify_pc_r10_command import (AssignmentOracle, Boundary, Snapshot, locate,
                                    candidates, checked, SPECIMEN, STACK, require)

PAGE = 4096
CONTEXT_BYTES = 5608
CALL_TIMEOUT_MICROSECONDS = 2_000_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def publish(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    Path(path).chmod(0o600)


def checkpoint(path, value):
    temp = Path(str(path)+'.pending')
    with temp.open('wb') as stream:
        stream.write(canonical(value)+b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)
    descriptor = os.open(Path(path).parent, os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def cpu_identity(raw):
    """Unicorn 2.1.4 Linux x64 CPU-only uc_context, with no CPU bytes masked.

    uc_priv.h/uc.c: bytes 20:32 are inactive ramblock_freed, C padding and
    last_block. Keep raw evidence; these host-memory fields are not CPU state.
    The allocated FlatView pointer must be NULL; snapshot_level must be zero.
    """
    require(unicorn.__version__ == '2.1.4' and sys.byteorder == 'little'
            and ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_size_t) == 8,
            'unsupported CPU context ABI')
    require(len(raw) == CONTEXT_BYTES, 'CPU context size changed')
    size, mode, arch, level = struct.unpack_from('<Qiii', raw)
    require(size == CONTEXT_BYTES - 40 and mode == unicorn.UC_MODE_32
            and arch == unicorn.UC_ARCH_X86 and level == 0 and raw[32:40] == bytes(8),
            'CPU-only context header changed')
    return {'size': size, 'mode': mode, 'arch': arch, 'snapshot_level': level,
            'flatview': 0, 'payload_sha256': digest(raw[40:]),
            'comparison_policy': 'unicorn-2.1.4-linux-x64-cpu-only-exclude-20-through-31'}


class CompleteState:
    """Every mapped byte, including alignment padding, plus full CPU context."""
    def __init__(self, uc, directory):
        self.uc, self.directory = uc, Path(directory)
        self.regions = list(uc.mem_regions())
        require(sum(b-a+1 for a, b, _ in self.regions) <= 256*1024**2, 'mapped state ceiling')
        self.base = [bytes(uc.mem_read(a, b-a+1)) for a, b, _ in self.regions]
        self.baseline_cpu = uc.context_save()
        self.evidence_cpu = uc.context_save()
        uc.context_update(self.evidence_cpu)
        self.raw_cpu = bytes(self.evidence_cpu)
        cpu_identity(self.raw_cpu)
        records = []
        for index, ((start, end, permissions), raw) in enumerate(zip(self.regions, self.base)):
            name = f'base-{index}.bin'
            publish(self.directory/name, raw)
            records.append({'start': start, 'end_inclusive': end, 'permissions': permissions,
                            'file': name, 'sha256': digest(raw), 'bytes': len(raw)})
        publish(self.directory/'base-cpu.bin', self.raw_cpu)
        self.description = {'regions': records, 'cpu_file': 'base-cpu.bin',
                            'cpu_raw_sha256': digest(self.raw_cpu), 'cpu': cpu_identity(self.raw_cpu)}
        publish(self.directory/'base.json', canonical(self.description)+b'\n')

    def reset(self):
        require(list(self.uc.mem_regions()) == self.regions, 'mapping changed')
        for (start, _, _), raw in zip(self.regions, self.base):
            self.uc.mem_write(start, raw)
        self.uc.context_restore(self.baseline_cpu)
        self.uc.context_update(self.evidence_cpu)
        require(bytes(self.evidence_cpu) == self.raw_cpu, 'complete CPU reset failed')
        require(all(bytes(self.uc.mem_read(a, len(raw))) == raw
                    for (a, _, _), raw in zip(self.regions, self.base)), 'complete mapped reset failed')

    def save(self, label):
        require(list(self.uc.mem_regions()) == self.regions, 'mapping changed')
        changes, regions = [], []
        for index, ((start, _, _), baseline) in enumerate(zip(self.regions, self.base)):
            raw = bytes(self.uc.mem_read(start, len(baseline)))
            pages = []
            for offset in range(0, len(raw), PAGE):
                page = raw[offset:offset+PAGE]
                if page != baseline[offset:offset+PAGE]:
                    pages.append({'offset': offset, 'data_offset': len(changes)*PAGE,
                                  'bytes': len(page), 'sha256': digest(page)})
                    changes.append(page)
            regions.append({'region': index, 'sha256': digest(raw), 'pages': pages})
        raw_delta = b''.join(changes)
        self.uc.context_update(self.evidence_cpu)
        cpu = bytes(self.evidence_cpu)
        publish(self.directory/(label+'.delta'), raw_delta)
        publish(self.directory/(label+'.cpu'), cpu)
        state = {'regions': regions, 'delta_file': label+'.delta', 'delta_sha256': digest(raw_delta),
                 'cpu_file': label+'.cpu', 'cpu_raw_sha256': digest(cpu), 'cpu': cpu_identity(cpu)}
        # Verify losslessness immediately, using the same independently usable decoder.
        reconstruct(self.directory, self.description, state)
        return state

    def unchanged_except(self, target, value):
        """Expected bytes derive solely from baseline and fixed admitted write."""
        hashes = []
        for (start, end, _), original in zip(self.regions, self.base):
            if start == STACK and end+1 == STACK+0x10000:
                continue  # Complete ABI stack is retained, but is explicitly mutable.
            expected = bytearray(original)
            if value is not None and start <= target and target+4 <= end+1:
                expected[target-start:target-start+4] = struct.pack('<I', value)
            require(bytes(self.uc.mem_read(start, len(original))) == expected,
                    'untouched mapped memory changed')
            hashes.append(digest(expected))
        return hashes


def reconstruct(directory, base, state):
    """Losslessly reconstruct all memory; reject omissions, duplicate or bad pages."""
    directory = Path(directory)
    delta = (directory/state['delta_file']).read_bytes()
    require(digest(delta) == state['delta_sha256'], 'delta hash')
    require(len(state['regions']) == len(base['regions']), 'missing mapped region')
    result, cursor, previous_end = [], 0, -1
    for index, (initial, item) in enumerate(zip(base['regions'], state['regions'])):
        require(item['region'] == index and initial['start'] > previous_end,
                'region ordering/overlap')
        previous_end = initial['end_inclusive']
        raw = bytearray((directory/initial['file']).read_bytes())
        require(len(raw) == initial['bytes'] == previous_end-initial['start']+1
                and len(raw) % PAGE == 0 and digest(raw) == initial['sha256'], 'base extent/hash')
        prior = -PAGE
        for page in item['pages']:
            offset = page['offset']
            require(offset % PAGE == 0 and offset > prior and offset+PAGE <= len(raw)
                    and page['bytes'] == PAGE and page['data_offset'] == cursor,
                    'delta extent/order')
            patch = delta[cursor:cursor+PAGE]
            require(len(patch) == PAGE and digest(patch) == page['sha256'], 'delta page hash')
            raw[offset:offset+PAGE] = patch
            cursor += PAGE
            prior = offset
        require(digest(raw) == item['sha256'], 'reconstructed region hash')
        result.append(bytes(raw))
    require(cursor == len(delta), 'unreferenced delta bytes')
    cpu = (directory/state['cpu_file']).read_bytes()
    require(digest(cpu) == state['cpu_raw_sha256'] and cpu_identity(cpu) == state['cpu'], 'CPU evidence')
    return result


class MatrixOracle(AssignmentOracle):
    def __init__(self, *args):
        self.events = []
        super().__init__(*args)
        self.decoder.detail = True
        self.trace_stream = None
        self.uc.hook_add(unicorn.UC_HOOK_MEM_INVALID, self.invalid)

    def record(self, event):
        event['sequence'] = len(self.events)+1
        self.events.append(event)
        if self.trace_stream is not None:
            self.trace_stream.write(canonical(event)+b'\n')
            self.trace_stream.flush()
            if len(self.events) % 16 == 0:
                self.flush_trace()

    def flush_trace(self):
        if self.trace_stream is not None:
            self.trace_stream.flush()
            os.fsync(self.trace_stream.fileno())
            prefix = b''.join(canonical(event)+b'\n' for event in self.events)
            checkpoint(Path(str(self.trace_stream.name)+'.durable.json'), {
                'trace_file': Path(self.trace_stream.name).name, 'durable_through_sequence': len(self.events),
                'prefix_bytes': len(prefix), 'prefix_sha256': digest(prefix)})

    def instruction(self, uc, address, size, unused):
        self.record({'kind': 'instruction', 'address': address, 'bytes': size})
        super().instruction(uc, address, size, unused)
        ins = next(self.decoder.disasm(bytes(uc.mem_read(address, size)), address))
        if ins.mnemonic == 'call':
            self.record({'kind': 'call', 'pc': address, 'target': int(ins.op_str, 16)})
        stack_access = None
        if ins.mnemonic in ('push', 'call'):
            stack_access = uc.reg_read(UC_X86_REG_ESP)-4
        elif ins.mnemonic in ('pop', 'ret'):
            stack_access = uc.reg_read(UC_X86_REG_ESP)
        elif ins.mnemonic == 'leave':
            stack_access = uc.reg_read(UC_X86_REG_EBP)
        if stack_access is not None and not STACK <= stack_access <= STACK+0x10000-4:
            self.censor('stack', 'outside-ABI-stack', 4)
        # Unicorn's write hook may run after effects have begun. Preflight every
        # explicit memory operand at the code boundary before this instruction.
        if ins.mnemonic != 'lea':
            for operand in ins.operands:
                if operand.type != capstone.x86.X86_OP_MEM:
                    continue
                memory = operand.mem
                if memory.segment:
                    self.censor('address', 'unqualified-segment')
                def reg_value(identifier):
                    return 0 if not identifier else uc.reg_read(getattr(registers, 'UC_X86_REG_'+ins.reg_name(identifier).upper()))
                target = (reg_value(memory.base)+reg_value(memory.index)*memory.scale+memory.disp) & 0xffffffff
                width = operand.size
                stack = STACK <= target and target+width <= STACK+0x10000
                if operand.access == 0:
                    self.censor('address', 'unqualified-memory-access-mode', width)
                if operand.access & capstone.CS_AC_READ and not stack and (target, width) not in self.fields.values():
                    self.record({'kind': 'denied-read', 'address': target, 'bytes': width, 'pc': address})
                    self.censor('read', 'outside-frozen-fields', width)
                if operand.access & capstone.CS_AC_WRITE and not stack and (target, width) not in self.allowed_writes:
                    self.record({'kind': 'denied-write', 'address': target, 'bytes': width, 'pc': address})
                    self.censor('write', 'outside-selected-slot', width)

    def read(self, uc, access, address, size, value, unused):
        self.record({'kind': 'read', 'address': address, 'bytes': size, 'pc': self.pc})
        super().read(uc, access, address, size, value, unused)

    def write(self, uc, access, address, size, value, unused):
        self.record({'kind': 'write', 'address': address, 'bytes': size,
                            'value': value, 'pc': self.pc})
        super().write(uc, access, address, size, value, unused)

    def invalid(self, uc, access, address, size, value, unused):
        self.pc = uc.reg_read(UC_X86_REG_EIP)
        if access in (unicorn.UC_MEM_FETCH_UNMAPPED, unicorn.UC_MEM_FETCH_PROT):
            self.decoded = None
        self.record({'kind': 'invalid-memory', 'access': access, 'address': address,
                            'bytes': size, 'value': value, 'pc': self.pc})
        self.censor('memory', 'unmapped-or-protected', size)

    def censor(self, kind, field, width=None):
        self.uc.emu_stop()
        self.flush_trace()
        super().censor(kind, field, width)

    def call(self, entry, arguments, receiver, allowed=(), expected=None):
        uc, sp = self.uc, STACK+0x8000
        self.pc, self.decoded, self.boundary = entry, None, None
        uc.mem_write(STACK, bytes(0x10000))
        uc.mem_write(sp, struct.pack('<'+'I'*(len(arguments)+1), STOP, *arguments))
        uc.reg_write(UC_X86_REG_ESP, sp)
        uc.reg_write(UC_X86_REG_ECX, receiver)
        uc.reg_write(UC_X86_REG_EIP, entry)
        saved = {UC_X86_REG_EBX: 0x12345678, UC_X86_REG_ESI: 0x23456789,
                 UC_X86_REG_EDI: 0x3456789a, UC_X86_REG_EBP: 0x456789ab}
        for reg, value in saved.items():
            uc.reg_write(reg, value)
        self.writes, self.reads, self.allowed_writes = [], set(), list(allowed)
        self.abi = {'entry': entry, 'arguments': arguments, 'receiver': receiver,
                    'entry_esp': sp, 'return_pc': STOP, 'expected_esp': sp+4*(len(arguments)+1),
                    'expected_eax': expected, 'expected_saved': saved}
        self.before_entry()
        try:
            uc.emu_start(entry, STOP, timeout=CALL_TIMEOUT_MICROSECONDS, count=3000)
        except unicorn.UcError:
            if self.boundary is not None:
                raise Boundary('frozen memory boundary') from None
            self.censor('emulator-error', 'unqualified-emulator-exit')
        self.abi.update(actual_pc=uc.reg_read(UC_X86_REG_EIP), actual_esp=uc.reg_read(UC_X86_REG_ESP),
                        actual_eax=uc.reg_read(UC_X86_REG_EAX), actual_saved={r: uc.reg_read(r) for r in saved})
        if self.abi['actual_pc'] != STOP:
            self.censor('execution-limit', 'no-return-before-time-or-instruction-limit')
        require(self.abi['actual_esp'] == self.abi['expected_esp'] and self.abi['actual_saved'] == saved,
                'ABI mismatch')
        require(self.abi['actual_eax'] == expected, 'return mismatch')
        return self.abi['actual_eax'], self.abi


def scientific(state):
    return {'mapped_sha256': [item['sha256'] for item in state['regions']], 'cpu': state['cpu']}


def verify_call(observed, kind, candidate, expected_hashes):
    expected = [] if kind == 'read' else [{'field': 'slot_zero', 'width': 4, 'candidate': candidate}]
    require(observed['writes'] == expected and observed['write_pcs'] ==
            ([] if kind == 'read' else ['00896b98']), 'ordered admitted effects')
    require(observed['return'] == (candidate if kind == 'read' else 'success-one')
            and observed['abi_checked'] is True, 'return or ABI')
    require(observed['no_rng_path'] is True and observed['expected_memory_sha256'] == expected_hashes,
            'RNG path or untouched memory')


def controls(observed, kind, candidate, expected):
    mutations = {'wrong-return': lambda x: x.update(returned='wrong', **{'return': 'wrong'}),
                 'unchecked-ABI': lambda x: x.update(abi_checked=False),
                 'extra-RNG': lambda x: x.update(no_rng_path=False),
                 'untouched-memory': lambda x: x.update(expected_memory_sha256=['0'*64])}
    if kind == 'assign':
        mutations.update({'omitted-write': lambda x: x.update(writes=[]),
                          'wrong-width': lambda x: x['writes'][0].update(width=2),
                          'wrong-member': lambda x: x['writes'][0].update(candidate=1-candidate),
                          'wrong-slot': lambda x: x['writes'][0].update(field='other_slot'),
                          'wrong-PC': lambda x: x.update(write_pcs=['00000000']),
                          'extra-write': lambda x: x['writes'].append(copy.deepcopy(x['writes'][0]))})
    else:
        mutations['read-mutation'] = lambda x: x.update(writes=[{'field': 'slot_zero'}])
    result = {}
    for name, mutate in mutations.items():
        changed = copy.deepcopy(observed)
        mutate(changed)
        try:
            verify_call(changed, kind, candidate, expected)
        except ValueError:
            result[name] = True
        else:
            raise ValueError('nondiscriminating control '+name)
    return result


def execute(binary, capture, output, job_id):
    binary, capture = Path(binary), Path(capture)
    out = Path(output)
    planned = next((j['cases'] for j in definition()['jobs'] if j['job_id'] == job_id), None)
    require(planned is not None, 'job outside frozen matrix')
    cases = [{'case': c, 'status': 'unstarted', 'calls': [
        {'kind': kind, 'candidate': candidate, 'status': 'unstarted'}
        for kind, candidate in [('assign', x) for x in c['assignments']]+[('read', c['assignments'][-1])]]}
        for c in planned]
    evidence = {'schema_version': 1, 'job_id': job_id, 'cases': cases}
    checkpoint(out/'lab007-checkpoint.json', evidence)
    endpoint = {'execution_status': 'failed', 'comparison_verdict': 'not-comparable', 'details': {}}
    try:
        raw, snapshot = checked(binary, SPECIMEN), Snapshot(capture)
        state = locate(snapshot)
        chosen, identity = candidates(snapshot, state)
        accepted = json.loads((Path(__file__).resolve().parents[1]/
                               'docs/research/evidence/pc-r10-command-retained-oracle-v1.json').read_text())
        require(identity == accepted['initialized_lifetime'], 'R10 admitted two-record identity changed')
        oracle = MatrixOracle(raw, snapshot, state, chosen)
        complete = CompleteState(oracle.uc, out)
        evidence.update(base=complete.description, initialized_lifetime=identity)
        for number, item in enumerate(cases):
            case = item['case']
            complete.reset()
            oracle.starts, oracle.calls = set(), []
            oracle.target = state['mapping']+state['club_id']*145+2+4*case['slot']
            oracle.fields['slot_zero'] = (oracle.target, 4)
            item['reset'] = complete.save(f"case-{case['case_id']}-reset")
            item['reset_verified'] = True
            item['status'] = 'started'
            checkpoint(out/'lab007-checkpoint.json', evidence)
            current = None
            sequence = [('assign', c) for c in case['assignments']] + [('read', case['assignments'][-1])]
            for index, (kind, candidate) in enumerate(sequence):
                oracle.events, oracle.current_starts, oracle.ordered_reads, oracle.write_pcs = [], [], [], []
                oracle.boundary = None
                label = f"case-{case['case_id']}-call-{index}"
                call = item['calls'][index]
                call.update(status='started', trace_file=label+'.trace.jsonl')
                checkpoint(out/'lab007-checkpoint.json', evidence)
                oracle.trace_stream = (out/call['trace_file']).open('xb')
                def before_entry():
                    call.update(before=complete.save(label+'-before'), abi=copy.deepcopy(oracle.abi))
                    checkpoint(out/'lab007-checkpoint.json', evidence)
                oracle.before_entry = before_entry
                args = [state['club'], case['slot'], 0] if kind == 'read' else [
                        state['club'], case['slot'], chosen[candidate][1], 0]
                try:
                    oracle.call(0x8968f0 if kind == 'read' else 0x896a90, args, state['context'],
                                [] if kind == 'read' else [(oracle.target, 4)],
                                chosen[candidate][1] if kind == 'read' else 1)
                    if kind == 'assign':
                        current = candidate
                    expected = complete.unchanged_except(oracle.target, chosen[current][0])
                    observed = {'writes': copy.deepcopy(oracle.writes), 'write_pcs': oracle.write_pcs[:],
                                'return': candidate if kind == 'read' else 'success-one', 'abi_checked': True,
                                'no_rng_path': True, 'expected_memory_sha256': expected}
                    verify_call(observed, kind, candidate, expected)
                    call.update(observed=observed, controls=controls(observed, kind, candidate, expected), status='passed')
                except Boundary:
                    call.update(status='censored', boundary=copy.deepcopy(oracle.boundary))
                    item['status'] = 'censored'
                except Exception as error:
                    call.update(status='failed', error={'type': type(error).__name__, 'reason': str(error)})
                    raise
                finally:
                    oracle.flush_trace()
                    oracle.trace_stream.close()
                    oracle.trace_stream = None
                    call.update(after=complete.save(label+'-after'), events=copy.deepcopy(oracle.events),
                                partial_writes=copy.deepcopy(oracle.writes),
                                pc=oracle.uc.reg_read(UC_X86_REG_EIP), eax=oracle.uc.reg_read(UC_X86_REG_EAX),
                                abi=copy.deepcopy(oracle.abi))
                    publish(out/(label+'.json'), canonical(call)+b'\n')
                    checkpoint(out/'lab007-checkpoint.json', evidence)
                if call['status'] == 'censored':
                    break
            if item['status'] == 'started':
                item['status'] = 'passed'
            publish(out/f"case-{case['case_id']}.json", canonical(item)+b'\n')
            checkpoint(out/'lab007-checkpoint.json', evidence)
            temp = out/'progress.lab007.tmp'
            temp.write_bytes(canonical({'sequence': number+1}))
            temp.replace(out/'progress.json')
        passed = sum(c['status'] == 'passed' for c in cases)
        endpoint.update(execution_status='succeeded', comparison_verdict='equal' if passed == 10 else 'inconclusive')
    except Exception as error:
        for item in cases:
            if item['status'] == 'started':
                item['status'] = 'failed'
        evidence['error'] = {'type': type(error).__name__, 'reason': str(error)}
    finally:
        science = copy.deepcopy(evidence)
        if 'base' in science:
            science['base'].pop('cpu_raw_sha256')
        for item in science['cases']:
            if 'reset' in item:
                item['reset'] = scientific(item['reset'])
            for call in item['calls']:
                for key in ('before', 'after'):
                    if key in call:
                        call[key] = scientific(call[key])
        publish(out/'lab007-evidence.json', canonical(evidence)+b'\n')
        checkpoint(out/'lab007-checkpoint.json', evidence)
        publish(out/'lab007-scientific.json', canonical(science)+b'\n')
        endpoint['details'] = {'planned_cases': 10, 'status_counts': {
            k: sum(c['status'] == k for c in cases) for k in ('passed', 'failed', 'censored', 'unstarted')},
            'scientific_sha256': digest(canonical(science)+b'\n'), 'production_admission': 'none',
            'original_process_launched': False, 'job_id': job_id}
        publish(out/'lab007-result.json', canonical(endpoint)+b'\n')
    return 0 if endpoint['execution_status'] == 'succeeded' else 1


if __name__ == '__main__':
    if len(sys.argv) != 5:
        raise SystemExit('binary capture output frozen-job-id required')
    raise SystemExit(execute(*sys.argv[1:]))
