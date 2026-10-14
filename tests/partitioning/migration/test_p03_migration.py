import pytest

from labs.partitioning.migration.store import Migration


def test_paused_copy_preserves_rows() -> None:
    migration = Migration(("a",))
    for key in range(6): migration.write(key, key)
    migration.pause_and_copy(("a", "b"))
    assert [migration.read(key) for key in range(6)] == list(range(6))
    with pytest.raises(RuntimeError): migration.write(8, 8)


def test_delta_replay_is_idempotent() -> None:
    migration = Migration(("a",)); migration.write(1, 1); since = migration.start_copy(("a", "b")); migration.write(1, 2); migration.write(2, 2)
    seen: set[int] = set(); assert migration.apply_delta(("a", "b"), since, seen) == 2; assert migration.apply_delta(("a", "b"), since, seen) == 0


def test_cutover_rejects_stale_route_and_fence() -> None:
    migration = Migration(("a",)); migration.write(1, 1); barrier = migration.sequence; migration.cutover(("a", "b"), barrier)
    with pytest.raises(ValueError): migration.write(1, 2, route_version=1)
    with pytest.raises(ValueError): migration.fence_old_owner("a", migration.fence - 1)
