from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from labs.recovery.backup.common import wal_segment_names


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/09-recovery/01-backup"
TARGETS = {version: ["common.py", f"v{version}.py"] for version in range(5)}


def test_wal_segment_names_preserve_postgresql_16_digit_suffix() -> None:
    assert wal_segment_names(
        "000000010000000000000002", "000000010000000000000009"
    ) == [
        "000000010000000000000002",
        "000000010000000000000003",
        "000000010000000000000004",
        "000000010000000000000005",
        "000000010000000000000006",
        "000000010000000000000007",
        "000000010000000000000008",
        "000000010000000000000009",
    ]


def extract(version: int, destination: Path) -> Path:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
    expected = [f"labs/recovery/backup/{name}" for name in TARGETS[version]]
    assert [path for path, _ in blocks] == expected
    package = destination / "labs/recovery/backup"
    package.mkdir(parents=True)
    for path, code in blocks:
        source = ROOT / path
        assert code.rstrip() == source.read_text().rstrip(), path
        (package / Path(path).name).write_text(code + "\n")
    (package / "__init__.py").write_text("")
    return package / f"v{version}.py"


@pytest.mark.parametrize("version", range(5))
def test_real_postgres_backup_restore(version: int, tmp_path: Path) -> None:
    assert os.environ.get("A01_DATABASE_URL") == "postgresql://a01:a01_local_only@127.0.0.1:55452/a01"
    script = extract(version, tmp_path)
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path / "labs/recovery/backup")}, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    if version == 0:
        assert output["round_trip"] and output["source_preserved"]
        assert output["duplicate_sqlstate"] == "23505" and output["null_sqlstate"] == "23502"
    elif version == 1:
        assert output["post_backup_row_excluded"] and output["source_preserved"]
    elif version == 2:
        assert output["corruption_detected"] and not output["partial_restore_accepted"]
    elif version == 3:
        assert output["physical_backup"] and output["base_backup_complete"] and output["deleted_row_restored"] and output["later_rows_absent"] and output["archive_continuous"] and output["required_wal_segments"]
    else:
        assert output["missing_archive_detected"] and output["recovery_failed"] and output["successful_recovery"]
        assert output["recovery_elapsed_seconds"] > 0 and output["failed_attempt_elapsed_seconds"] > 0
        assert output["acknowledged_rows_before_target"] == 2 and output["recovered_rows"] == "1:100,2:100"
        assert output["post_target_rows_not_recovered"] == 1 and output["data_loss_window"]


def test_all_chapters_have_exact_python_fences() -> None:
    for version, names in TARGETS.items():
        text = (GUIDES / f"v{version}/tutorial.md").read_text()
        paths = [Path(path).name for path, _ in re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)]
        assert paths == names


