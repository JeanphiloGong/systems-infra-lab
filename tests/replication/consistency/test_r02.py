from __future__ import annotations

import pytest

from labs.replication.consistency import v0, v1, v2, v3, v4


def test_v0_stale_read_then_eventual_convergence() -> None:
    store = v0.ReplicaSet()
    store.write("name", "Ada")
    assert store.read_replica("name") is None
    store.converge()
    assert store.read_replica("name") == "Ada"


def test_v1_session_reads_own_write_but_other_replica_read_is_old() -> None:
    store = v1.ReplicaSet()
    session = v1.Session()
    version = session.write(store, "name", "Ada")
    assert session.read(store, "name") == (version, "Ada")
    assert store.read_replica("name") is None


def test_v2_single_writer_history_is_checkable() -> None:
    store = v2.LinearizableStore()
    store.write("name", "Ada")
    assert store.read("name") == "Ada"
    assert store.check_history()


def test_v3_repairs_only_the_replica_key_that_was_read() -> None:
    store = v3.ReadRepairStore()
    store.write("name", "Ada", 2)
    store.write("city", "Paris", 2)
    store.seed_replica(0, "name", 1, "A.")
    store.seed_replica(0, "city", 1, "London")
    assert store.read_with_repair(0, "name") == (2, "Ada")
    assert store.replicas[0]["name"] == (2, "Ada")
    assert store.replicas[0]["city"] == (1, "London")


def test_v4_contracts_and_partition_boundary() -> None:
    store = v4.VersionedStore()
    version = store.write("name", "Ada")
    assert store.read("name", v4.Contract.EVENTUAL) == v4.Read("Ada", version)
    assert store.read("name", v4.Contract.SESSION, session_version=version) == v4.Read("Ada", version)
    assert store.read("name", v4.Contract.SNAPSHOT, snapshot_version=version) == v4.Read("Ada", version)
    store.partitioned = True
    with pytest.raises(ConnectionError):
        store.read("name", v4.Contract.LINEARIZABLE)
