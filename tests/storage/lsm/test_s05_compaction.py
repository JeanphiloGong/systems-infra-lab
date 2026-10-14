import json
from pathlib import Path

import pytest

from labs.storage.lsm.compaction import compact
from labs.storage.lsm.sstable import SSTable
from labs.storage.lsm.tombstones import TombstoneStore


def test_partial_retains_delete_before_unseen_older_file(tmp_path: Path) -> None:
    old = TombstoneStore.create(tmp_path / "old.sst", {"k": "old", "keep": "old"}).path
    deleted = TombstoneStore.create(tmp_path / "deleted.sst", {"k": None}).path
    new = TombstoneStore.create(tmp_path / "new.sst", {"keep": "new"}).path
    result = compact([new, deleted, old], 0, 2, tmp_path / "partial.sst")
    assert result == [tmp_path / "partial.sst", old]
    assert TombstoneStore(result).get("k") is None
    assert TombstoneStore(result).get("keep") == "new"
    assert json.loads(SSTable(result[0]).get("k")) == ["delete"]
    assert all(path.exists() for path in (new, deleted, old))


def test_full_drops_delete_and_preserves_arbitrary_values(tmp_path: Path) -> None:
    old = TombstoneStore.create(tmp_path / "old.sst", {"k": "old", "a": "old"}).path
    new = TombstoneStore.create(tmp_path / "new.sst", {"k": None, "a": "", "tag": "__TOMBSTONE__"}).path
    result = compact([new, old], 0, 2, tmp_path / "full.sst")
    assert list(SSTable(result[0]).items()) == [("a", '["value", ""]'), ("tag", '["value", "__TOMBSTONE__"]')]
    assert TombstoneStore(result).get("k") is None
    assert TombstoneStore(result).get("a") == ""


def test_oldest_suffix_can_drop_but_keeps_newer_priority(tmp_path: Path) -> None:
    old = TombstoneStore.create(tmp_path / "old.sst", {"k": "old"}).path
    deleted = TombstoneStore.create(tmp_path / "deleted.sst", {"k": None}).path
    newest = TombstoneStore.create(tmp_path / "newest.sst", {"k": "reborn"}).path
    result = compact([newest, deleted, old], 1, 3, tmp_path / "suffix.sst")
    assert result[0] == newest
    assert list(SSTable(result[1]).items()) == []
    assert TombstoneStore(result).get("k") == "reborn"


@pytest.mark.parametrize("start,stop", [(-1,1), (0,0), (1,0), (0,2)])
def test_bad_range_publishes_nothing(tmp_path: Path, start: int, stop: int) -> None:
    output = tmp_path / "result.sst"
    with pytest.raises(ValueError):
        compact([tmp_path / "input.sst"], start, stop, output)
    assert not output.exists()


def test_bad_tag_even_if_shadowed_rejects_merge(tmp_path: Path) -> None:
    good = TombstoneStore.create(tmp_path / "good.sst", {"k": "new"}).path
    bad = SSTable.create(tmp_path / "bad.sst", {"k": '["unknown"]'}).path
    with pytest.raises(ValueError, match="tagged"):
        compact([good, bad], 0, 2, tmp_path / "result.sst")
    assert not (tmp_path / "result.sst").exists()


@pytest.mark.parametrize("start,stop", [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)])
def test_every_contiguous_interval_preserves_reads(tmp_path: Path, start: int, stop: int) -> None:
    snapshots = [
        {"a": None, "b": "new", "empty": ""},
        {"a": "middle", "b": None, "c": None},
        {"a": "old", "b": "old", "c": "old", "tail": "yes"},
    ]
    files = [TombstoneStore.create(tmp_path / f"{index}.sst", data).path for index, data in enumerate(snapshots)]
    keys = ["a", "b", "c", "tail", "empty", "missing"]
    before = [TombstoneStore(files).get(key) for key in keys]
    replacement = compact(files, start, stop, tmp_path / "result.sst")
    assert [TombstoneStore(replacement).get(key) for key in keys] == before
    assert replacement[:start] == files[:start]
    assert replacement[start+1:] == files[stop:]


def test_existing_output_is_immutable_and_inputs_retained(tmp_path: Path) -> None:
    file = TombstoneStore.create(tmp_path / "input.sst", {"k": "value"}).path
    before = file.read_bytes()
    with pytest.raises(FileExistsError):
        compact([file], 0, 1, file)
    assert file.read_bytes() == before
