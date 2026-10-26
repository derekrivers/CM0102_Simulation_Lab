"""Proposed LAB-007 case identities only; contains no execution capability."""
import hashlib
import json


def matrix():
    cases = []
    for slot in range(20):
        for first in range(2):
            for sequence in ('assign-read', 'repeat-read', 'replace-read'):
                assignments = [first]
                if sequence == 'repeat-read':
                    assignments.append(first)
                elif sequence == 'replace-read':
                    assignments.append(1 - first)
                cases.append({'case_id': f'{len(cases) + 1:03d}', 'slot': slot,
                              'first_member': first, 'sequence': sequence,
                              'assignments': assignments, 'final_operation': 'read'})
    return cases


def definition():
    cases = matrix()
    raw = json.dumps(cases, sort_keys=True, separators=(',', ':')).encode()
    return {'schema_version': 1, 'campaign': 'LAB-007', 'execution_approved': False,
            'case_list_sha256': hashlib.sha256(raw).hexdigest(),
            'case_order': 'slot ascending, first member 0 then 1, assign/repeat/replace',
            'member_identity': 'same two independently admitted R10 actual members; labels only',
            'reset': 'complete admitted state before every case',
            'jobs': [{'job_id': f'{i // 10 + 1:03d}-retained-assignment', 'cases': cases[i:i + 10]}
                     for i in range(0, len(cases), 10)]}


if __name__ == '__main__':
    print(json.dumps(definition(), indent=2))
