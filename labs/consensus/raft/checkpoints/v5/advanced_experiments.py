from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from .advanced import Cluster, Node


def crashes(directory):
    outcomes = {}
    for action in ('vote', 'append', 'commit', 'snapshot'):
        for fault, expected_code in [('before_replace', 71), ('after_replace', 72), ('after_directory_sync', 73)]:
            case = directory / (action + '-' + fault)
            case.mkdir()
            node = Node('a', ('a', 'b', 'c'), case)
            node.term = 1
            node.role = 'leader'
            node.match = dict(a=0, b=0, c=0)
            node.next = dict(a=1, b=1, c=1)
            node.persist()
            if action in ('commit', 'snapshot'):
                node.append('mode', 'saved')
            if action == 'snapshot':
                node.apply(1)
            worker = """import sys
from pathlib import Path
from labs.consensus.raft.advanced import Node
n=Node('a',('a','b','c'),Path(sys.argv[1]))
n.fault=sys.argv[3]
action=sys.argv[2]
if action=='vote': n.campaign()
elif action=='append':
 n.role='leader'; n.match=dict(a=0,b=0,c=0); n.next=dict(a=1,b=1,c=1); n.append('mode','saved')
elif action=='commit': n.apply(1)
else: n.compact()
"""
            killed = subprocess.run([sys.executable, '-c', worker, str(case), action, fault], timeout=10)
            assert killed.returncode == expected_code
            recovered = Node('a', ('a', 'b', 'c'), case)
            published = fault != 'before_replace'
            if action == 'vote':
                assert recovered.term == (2 if published else 1)
                assert recovered.vote == ('a' if published else None)
            if action == 'append':
                assert recovered.last == (1 if published else 0)
                assert recovered.state == {}
            if action == 'commit':
                assert recovered.commit == (1 if published else 0)
                assert recovered.state == ({'mode': 'saved'} if published else {})
            if action == 'snapshot':
                assert recovered.base == (1 if published else 0)
                assert recovered.last == recovered.commit == 1
                assert recovered.state == {'mode': 'saved'}
            outcomes[action + ':' + fault] = dict(exit=killed.returncode, commit=recovered.commit, base=recovered.base)
    return outcomes


def run(version=5):
    if version != 5:
        raise ValueError('this checkpoint runs version 5')
    with TemporaryDirectory() as folder:
        return crashes(Path(folder))


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
