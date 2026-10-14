import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from labs.storage.lsm.sstable import SSTable


def test_sorted_utf8_roundtrip_and_no_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "one.sst"
    values = {"z": "line\nbreak", "a": "", "中文": "引号\"与\\"}
    table = SSTable.create(path, values)
    assert list(table.items()) == sorted(values.items())
    assert table.get("a") == ""
    assert table.get("missing") is None
    assert SSTable(path).get("中文") == values["中文"]
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        SSTable.create(path, {"different": "value"})
    assert path.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["one.sst"]


def test_fresh_process_reopens_file(tmp_path: Path) -> None:
    path = tmp_path / "reopen.sst"
    SSTable.create(path, {"k": "saved"})
    result = subprocess.run(
        [sys.executable, "-c", "from pathlib import Path; from labs.storage.lsm.sstable import SSTable; import sys; print(SSTable(Path(sys.argv[1])).get('k'))", str(path)],
        env={**os.environ, "PYTHONPATH": str(Path.cwd())},
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "saved"


@pytest.mark.parametrize("records", [ [["z","x"],["a","y"]], [["a","x"],["a","y"]], [["a",3]], [{"key":"a"}] ])
def test_corrupt_order_or_shape_is_rejected(tmp_path: Path, records: list[object]) -> None:
    path = tmp_path / "bad.sst"
    path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    with pytest.raises(ValueError):
        list(SSTable(path).items())


def test_empty_file_and_invalid_input_cleanup(tmp_path: Path) -> None:
    assert list(SSTable.create(tmp_path / "empty.sst", {}).items()) == []
    with pytest.raises(TypeError):
        SSTable.create(tmp_path / "invalid.sst", {"k": 3})  # type: ignore[dict-item]
    assert not (tmp_path / "invalid.sst").exists()
    assert len(list(tmp_path.iterdir())) == 1
