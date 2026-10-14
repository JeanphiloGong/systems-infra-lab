import copy

import pytest

from labs.consensus.raft.advanced import Cluster, Node
from labs.consensus.raft.advanced_experiments import run


@pytest.mark.parametrize('version', [1, 3, 4, 5, 6, 7])
def test_real_scenarios(version):
    assert run(version)


def test_acknowledgement_requires_follower_persistence(tmp_path):
    cluster = Cluster(tmp_path)
    cluster.timeout('a')
    cluster.drain()
    cluster.propose('a', 'x', '1')
    cluster.deliver()
    assert cluster.nodes['a'].commit == 0
    assert Node('b', cluster.members, tmp_path).last == 1
    ack_index = next(i for i, item in enumerate(cluster.queue) if item['kind'] == 'ack')
    cluster.deliver(ack_index)
    assert cluster.nodes['a'].commit == 1


def test_unknown_peer_cannot_supply_quorum(tmp_path):
    cluster = Cluster(tmp_path)
    with pytest.raises(ValueError, match='unknown peer'):
        cluster.nodes['a'].receive(dict(src='x', kind='ack', term=0))


def test_duplicate_and_stale_ack_do_not_move_commit_backwards(tmp_path):
    cluster = Cluster(tmp_path)
    cluster.timeout('a')
    cluster.drain()
    cluster.propose('a', 'x', '1')
    cluster.deliver()
    ack = copy.deepcopy(next(item for item in cluster.queue if item['kind'] == 'ack'))
    cluster.drain()
    cluster.propose('a', 'x', '2')
    cluster.drain()
    assert cluster.nodes['a'].receive(ack) == []
    assert cluster.nodes['a'].commit == 2


def test_snapshot_is_exact_committed_prefix_not_uncommitted_tail(tmp_path):
    cluster = Cluster(tmp_path)
    cluster.timeout('a')
    cluster.drain()
    cluster.propose('a', 'x', '1')
    cluster.drain()
    cluster.partition('a', 'bc')
    cluster.propose('a', 'x', '2')
    cluster.drain()
    leader = cluster.nodes['a']
    leader.compact()
    assert leader.base == 1 and leader.last == 2
    assert leader.snapshot_state == {'x': '1'}
    assert leader.log == [dict(term=1, key='x', value='2')]
    restarted = Node('a', cluster.members, tmp_path)
    assert restarted.base == 1 and restarted.last == 2 and restarted.commit == 1
    assert restarted.state == {'x': '1'}
