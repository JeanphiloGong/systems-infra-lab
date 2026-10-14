from dataclasses import replace

import pytest

from labs.replication.consistency.v2 import LinearizableStore, Operation, check_history
from labs.replication.consistency.v4 import Contract, Read, VersionedStore


def test_history_checks_values_keys_and_real_time():
    write = Operation('write', 'name', 'Ada', 1, 1, 2)
    read = Operation('read', 'name', 'Ada', None, 2, 3)
    assert check_history([read, write])
    assert not check_history([write, replace(read, value='WRONG')])
    assert not check_history([write, replace(read, key='city')])
    assert not check_history([write, replace(read, value=None)])
    assert check_history([write, replace(read, value=None, invoked=0, returned=3)])
    assert not check_history([write, replace(read, invoked=4, returned=3)])


def test_history_rejects_impossible_overlapping_cycle():
    history = [Operation('write', 'x', 'one', 1, 0, 3),
               Operation('read', 'x', 'one', None, 1, 2),
               Operation('read', 'x', None, None, 4, 5)]
    assert not check_history(history)
    store = LinearizableStore()
    store.write('name', 'Ada')
    store.read('name')
    assert store.history[0].returned <= store.history[1].invoked
    assert store.check_history()


def test_snapshot_retains_multikey_cut_across_updates():
    store = VersionedStore()
    store.write('name', 'Ada')
    cut = store.write('city', 'London')
    store.write('name', 'Grace')
    for _ in range(2):
        assert store.read('name', Contract.SNAPSHOT, snapshot_version=cut) == Read('Ada', 1)
        assert store.read('city', Contract.SNAPSHOT, snapshot_version=cut) == Read('London', 2)
        store.write('city', 'Paris')
    assert store.read('name', Contract.SNAPSHOT, snapshot_version=0) == Read(None, 0)


@pytest.mark.parametrize('existing', [False, True])
def test_session_partition_missing_and_stale_then_recovery(existing):
    store = VersionedStore()
    if existing:
        store.write('name', 'Ada')
    store.partitioned = True
    version = store.write('name', 'Grace')
    with pytest.raises(ConnectionError):
        store.read('name', Contract.SESSION, session_version=version)
    store.partitioned = False
    assert store.read('name', Contract.SESSION, session_version=version) == Read('Grace', version)
    store.catch_up()
    store.partitioned = True
    assert store.read('name', Contract.SESSION, session_version=version) == Read('Grace', version)
