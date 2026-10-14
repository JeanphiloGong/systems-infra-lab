import json
from pathlib import Path

from labs.storage.wal.prepared import prepare, inspect_pending


def test_prepared_intent_exists_before_data_changes(tmp_path: Path) -> None:
    data, log = tmp_path / "data.json", tmp_path / "wal.bin"
    data.write_text(json.dumps({"alice": 100, "bob": 100}))
    prepare(data, log, apply=False)
    candidate, pending = inspect_pending(log)
    assert candidate == {"alice": 90, "bob": 110}
    assert pending == {"t1"}
    assert json.loads(data.read_text()) == {"alice": 100, "bob": 100}
    assert inspect_pending(log) == (candidate, pending)


def test_apply_after_logging_is_still_uncommitted(tmp_path: Path) -> None:
    data, log = tmp_path / "data.json", tmp_path / "wal.bin"
    prepare(data, log, apply=True)
    assert json.loads(data.read_text()) == {"alice": 90, "bob": 110}
    assert inspect_pending(log)[1] == {"t1"}
