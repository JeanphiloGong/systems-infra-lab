from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .advanced import Cluster, Node


def election(directory):
    cluster = Cluster(directory)
    cluster.deadline = {name: 10 for name in cluster.members}
    cluster.tick(10)
    cluster.drain()
    assert all(node.role == 'candidate' for node in cluster.nodes.values())
    assert {node.term for node in cluster.nodes.values()} == {1}
    cluster.deadline = dict(a=20, b=21, c=22)
    cluster.tick(20)
    cluster.drain()
    assert cluster.nodes['a'].role == 'leader'
    cluster.restart('b')
    assert cluster.nodes['b'].vote == 'a'
    reply = cluster.nodes['b'].receive(dict(src='c', dst='b', kind='vote', term=2, last=0, last_term=0))
    assert not reply[0]['granted']
    worker = """import os,sys
from pathlib import Path
from labs.consensus.raft.advanced import Node
n=Node('b',('a','b','c'),Path(sys.argv[1]))
assert n.vote=='a' and n.term==2
assert not n.receive(dict(src='c',kind='vote',term=2,last=0,last_term=0))[0]['granted']
os._exit(74)
"""
    crashed = subprocess.run([sys.executable, '-c', worker, str(directory)], timeout=10)
    assert crashed.returncode == 74
    cluster.restart('b')
    assert cluster.nodes['b'].vote == 'a' and cluster.nodes['b'].term == 2
    return dict(simultaneous_candidates=3, elected_term=2, restart_vote=cluster.nodes['b'].vote,
                messages=len(cluster.trace), restart_exit=crashed.returncode)


def majority(directory):
    cluster = Cluster(directory)
    cluster.timeout('a')
    cluster.drain()
    cluster.partition('a', 'bc')
    cluster.propose('a', 'mode', 'old-term')
    cluster.drain()
    assert cluster.nodes['a'].commit == 0
    # A new election raises the term while retaining the previous uncommitted entry.
    cluster.blocked.clear()
    cluster.timeout('a')
    cluster.drain()
    assert all(node.last == 1 for node in cluster.nodes.values())
    assert all(node.commit == 0 for node in cluster.nodes.values())
    old_term_commit = cluster.nodes['a'].commit
    cluster.propose('a', 'mode', 'current-term')
    cluster.drain()
    assert all(node.commit == 2 and node.state == {'mode': 'current-term'}
               for node in cluster.nodes.values())
    unknown = dict(src='not-a-member', dst='a', kind='ack', term=2, request=999, ok=True, matched=999)
    try:
        cluster.nodes['a'].receive(unknown)
    except ValueError:
        pass
    else:
        raise AssertionError('unknown peer accepted')
    return dict(old_term_commit=old_term_commit, current_term_commit=2,
                durable_lengths=[Node(n, cluster.members, directory).last for n in cluster.members])


def freshness(directory):
    cluster = Cluster(directory)
    cluster.timeout('a')
    cluster.drain()
    cluster.partition('c', 'ab')
    cluster.propose('a', 'mode', 'committed')
    cluster.drain()
    assert cluster.nodes['a'].commit == cluster.nodes['b'].commit == 1
    cluster.blocked.clear()
    cluster.timeout('c')
    cluster.drain()
    assert cluster.nodes['c'].role == 'candidate'
    assert cluster.nodes['c'].votes == {'c'}
    cluster.timeout('b')
    cluster.drain()
    assert cluster.nodes['b'].role == 'leader'
    cluster.propose('b', 'next', 'kept')
    cluster.drain()
    assert all(node.state == {'mode': 'committed', 'next': 'kept'} for node in cluster.nodes.values())
    return dict(stale_candidate_votes=1, winner='b', preserved='committed')


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


def faults(directory):
    cluster = Cluster(directory)
    cluster.timeout('a')
    cluster.drain()
    cluster.propose('a', 'stable', 'yes')
    cluster.drain()
    cluster.partition('a', 'bc')
    cluster.propose('a', 'mode', 'orphan')
    cluster.drain()
    assert cluster.nodes['a'].commit == 1
    cluster.timeout('b')
    cluster.drain()
    cluster.propose('b', 'mode', 'successor')
    cluster.drain()
    assert cluster.nodes['b'].commit == cluster.nodes['c'].commit == 2
    assert cluster.nodes['a'].state == {'stable': 'yes'}
    cluster.blocked.clear()
    cluster.queue.extend(cluster.nodes['b'].broadcast())
    cluster.queue.extend(copy.deepcopy(cluster.queue))
    cluster.deliver(drop=True)
    cluster.drain(reverse=True)
    cluster.queue.extend(cluster.nodes['b'].broadcast())
    cluster.drain()
    assert all(node.commit == 2 and node.state == {'stable': 'yes', 'mode': 'successor'}
               for node in cluster.nodes.values())
    assert cluster.nodes['a'].role == 'follower'
    return dict(final_commit=2, state=cluster.nodes['a'].state, delivered=len(cluster.trace),
                dropped=sum(item['dropped'] for item in cluster.trace))


def snapshots(directory):
    cluster = Cluster(directory)
    cluster.timeout('a')
    cluster.drain()
    cluster.partition('c', 'ab')
    cluster.propose('a', 'x', '1')
    cluster.drain()
    cluster.propose('a', 'x', '2')
    cluster.drain()
    leader = cluster.nodes['a']
    leader.compact()
    assert leader.base == 2 and leader.last == 2 and leader.log == []
    cluster.propose('a', 'x', '3')
    cluster.drain()
    assert leader.last == 3 and len(leader.log) == 1
    assert leader.snapshot_state == {'x': '2'}
    cluster.blocked.clear()
    cluster.queue.extend(leader.broadcast())
    cluster.drain()
    cluster.restart('c')
    lagging = cluster.nodes['c']
    assert lagging.base == 2 and lagging.last == lagging.commit == 3
    assert lagging.state == {'x': '3'}
    assert any(message['kind'] == 'snapshot' for message in cluster.trace)
    return dict(base=lagging.base, last=lagging.last, commit=lagging.commit,
                snapshot=lagging.snapshot_state, state=lagging.state)


def run(version):
    with TemporaryDirectory() as folder:
        path = Path(folder)
        return {1: election, 3: majority, 4: freshness, 5: crashes, 6: faults, 7: snapshots}[version](path)


if __name__ == '__main__':
    print(json.dumps(run(int(sys.argv[1])), sort_keys=True))
