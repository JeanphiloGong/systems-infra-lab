from pathlib import Path
import pytest
from labs.storage.lsm.sstable import SSTable
from labs.storage.lsm.versions import VersionedStore
from labs.storage.lsm.tombstones import TombstoneStore


def test_newest_file_wins_and_reopen(tmp_path: Path) -> None:
    old = SSTable.create(tmp_path / "old.sst", {"k": "old", "keep": "yes"})
    new = SSTable.create(tmp_path / "new.sst", {"k": "new"})
    assert VersionedStore([new.path, old.path]).get("k") == "new"
    assert VersionedStore([new.path, old.path]).get("keep") == "yes"


def test_tombstone_survives_restart_and_hides_old(tmp_path: Path) -> None:
    old = TombstoneStore.create(tmp_path / "old.sst", {"k": "old"})
    deleted = TombstoneStore.create(tmp_path / "deleted.sst", {"k": None})
    assert TombstoneStore([deleted.path, old.path]).get("k") is None
    assert TombstoneStore([deleted.path, old.path]).get("missing") is None


def test_no_reserved_string_and_empty_values(tmp_path: Path) -> None:
    table = TombstoneStore.create(tmp_path / "all.sst", {"sentinel": "__TOMBSTONE__", "empty": "", "json": '["delete"]'})
    reopened = TombstoneStore([table.path])
    assert reopened.get("sentinel") == "__TOMBSTONE__"
    assert reopened.get("empty") == ""
    assert reopened.get("json") == '["delete"]'


def test_later_put_after_delete_and_empty_file(tmp_path: Path) -> None:
    old = TombstoneStore.create(tmp_path / "old.sst", {"k": "old"})
    deleted = TombstoneStore.create(tmp_path / "delete.sst", {"k": None})
    newest = TombstoneStore.create(tmp_path / "new.sst", {"k": "reborn"})
    empty = TombstoneStore.create(tmp_path / "empty.sst", {})
    assert TombstoneStore([empty.path, newest.path, deleted.path, old.path]).get("k") == "reborn"


def test_new_empty_string_overrides_old_value(tmp_path: Path) -> None:
    old = SSTable.create(tmp_path / "old.sst", {"k": "old"})
    new = SSTable.create(tmp_path / "new.sst", {"k": ""})
    assert VersionedStore([new.path, old.path]).get("k") == ""
    assert VersionedStore([]).get("k") is None


def test_bad_tag_not_treated_as_missing(tmp_path: Path) -> None:
    table = SSTable.create(tmp_path / "bad.sst", {"k": '["other"]'})
    with pytest.raises(ValueError, match="tagged"):
        TombstoneStore([table.path]).get("k")
    with pytest.raises(TypeError):
        TombstoneStore.create(tmp_path / "invalid.sst", {"k": 3})  # type: ignore[dict-item]
    assert not (tmp_path / "invalid.sst").exists()
