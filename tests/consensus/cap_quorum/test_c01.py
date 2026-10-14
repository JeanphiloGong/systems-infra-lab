from __future__ import annotations

import pytest

from labs.consensus.cap_quorum import v0, v1, v2, v3


def test_v0_timeout_cannot_classify_remote_operation() -> None:
    network = v0.Partition()
    message = network.send("A", "B", "apply:op-1")
    assert network.timeout("op-1") == "unknown"
    network.deliver(network.send("B", "A", "done:op-1"))
    assert network.timeout("op-1") == "completed"
    assert not message.delivered


def test_v1_lost_final_ack_leaves_coordination_incomplete() -> None:
    trace = v1.two_generals_trace()
    assert "ack lost" in trace
    assert v1.conclude(trace) == "coordination incomplete"


def test_v2_partition_exposes_cap_policy_choice() -> None:
    safe = v2.PartitionedStore(v2.Policy.REJECT_ON_PARTITION)
    safe.partitioned = True
    assert safe.read() == "unavailable"
    available = v2.PartitionedStore(v2.Policy.SERVE_OLD_READ)
    available.partitioned = True
    assert available.read() == "old"


def test_v3_intersection_and_quorum_values() -> None:
    nodes = {"a", "b", "c"}
    assert v3.has_intersection(nodes, 2, 2)
    assert not v3.has_intersection(nodes, 1, 1)
    replicas = {"a": (1, "old"), "b": (2, "new")}
    assert v3.quorum_read(nodes, replicas, 2) == (2, "new")
    with pytest.raises(ValueError):
        v3.quorum_read(nodes, replicas, 4)


def test_v3_pending_write_causes_new_then_old_read() -> None:
    observed = v3.concurrent_history()
    assert observed['intersection'] is True
    assert observed['read_quorums'] == [['a', 'b'], ['b', 'c']]
    assert observed['reads'] == [(1, 'new'), (0, 'old')]
    assert observed['trace'] == [
        'invoke write(new)', 'deliver write to a',
        'invoke read1(a,b)', 'return read1(new)',
        'invoke read2(b,c)', 'return read2(old)',
        'deliver write to b', 'return write(success)',
    ]
    assert observed['write_acks'] == 2
