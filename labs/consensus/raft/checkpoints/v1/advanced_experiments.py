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


def run(version=1):
    if version != 1:
        raise ValueError('this checkpoint runs version 1')
    with TemporaryDirectory() as folder:
        return election(Path(folder))


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
