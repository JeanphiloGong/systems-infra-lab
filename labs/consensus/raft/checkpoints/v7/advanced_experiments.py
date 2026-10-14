from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from .advanced import Cluster, Node


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


def run(version=7):
    if version != 7:
        raise ValueError('this checkpoint runs version 7')
    with TemporaryDirectory() as folder:
        return snapshots(Path(folder))


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
