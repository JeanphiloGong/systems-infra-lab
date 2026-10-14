from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from .advanced import Cluster, Node


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


def run(version=3):
    if version != 3:
        raise ValueError('this checkpoint runs version 3')
    with TemporaryDirectory() as folder:
        return majority(Path(folder))


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
