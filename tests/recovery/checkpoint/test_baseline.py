from pathlib import Path
import os
import re
import subprocess
import sys

import pytest

from labs.recovery.checkpoint.baseline import commit, recover


def test_replay_measures_actual_files(tmp_path: Path) -> None:
    assert recover(tmp_path) == ({"alice": 100, "bob": 100}, 0, 0)
    for number in range(1, 11):
        commit(tmp_path, number, {"alice": 100 - number, "bob": 100 + number})
    expected_bytes = sum(path.stat().st_size for path in tmp_path.glob("*.wal"))
    assert recover(tmp_path) == ({"alice": 90, "bob": 110}, 10, expected_bytes)
    (tmp_path / "unfinished.tmp").write_bytes(b"torn")
    assert recover(tmp_path) == ({"alice": 90, "bob": 110}, 10, expected_bytes)


def test_missing_middle_segment_fails(tmp_path: Path) -> None:
    for number in range(1, 4):
        commit(tmp_path, number, {"alice": 100, "bob": 100})
    (tmp_path / "00000000000000000002.wal").unlink()
    with pytest.raises(ValueError, match="gap"):
        recover(tmp_path)


def test_corrupt_and_truncated_published_segments_fail(tmp_path: Path) -> None:
    commit(tmp_path, 1, {"alice": 99, "bob": 101})
    path = tmp_path / "00000000000000000001.wal"
    data = path.read_bytes()
    path.write_bytes(data[:-1])
    with pytest.raises(ValueError, match="incomplete"):
        recover(tmp_path)
    damaged = bytearray(data)
    damaged[12] ^= 1
    path.write_bytes(damaged)
    with pytest.raises(ValueError, match="checksum"):
        recover(tmp_path)


def test_reject_invalid_transaction_before_publication(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        commit(tmp_path, 1, {"alice": -1, "bob": 201})
    assert list(tmp_path.iterdir()) == []
    commit(tmp_path, 1, {"alice": 99, "bob": 101})
    with pytest.raises(FileExistsError):
        commit(tmp_path, 1, {"alice": 98, "bob": 102})
    assert recover(tmp_path)[0] == {"alice": 99, "bob": 101}


def test_v0_tutorial_replays_from_exact_fences(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    document = (root / "tutorials/09-recovery/02-checkpoint/v0/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", document, re.S)
    assert [path for path, _ in blocks] == [
        "labs/storage/wal/framing.py",
        "labs/recovery/checkpoint/baseline.py",
    ]
    for relative, code in blocks:
        assert code.rstrip() == (root / relative).read_text().rstrip()
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code + "\n")
    (tmp_path / "labs/storage/wal/__init__.py").write_text("")
    (tmp_path / "labs/recovery/checkpoint/__init__.py").write_text("")
    probe = tmp_path / "run.py"
    probe.write_text(
        "from pathlib import Path\n"
        "from labs.recovery.checkpoint.baseline import commit, recover\n"
        "p=Path('segments'); p.mkdir()\n"
        "commit(p, 1, {'alice': 99, 'bob': 101})\n"
        "print(recover(p)[0])\n"
    )
    result = subprocess.run(
        [sys.executable, str(probe)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "{'alice': 99, 'bob': 101}"
