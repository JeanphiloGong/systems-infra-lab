from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from .advanced import Cluster, Node


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


def run(version=4):
    if version != 4:
        raise ValueError('this checkpoint runs version 4')
    with TemporaryDirectory() as folder:
        return freshness(Path(folder))


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
