import json
from pathlib import Path
import subprocess
import sys


def test_process_exit_leaves_half_transfer(tmp_path: Path) -> None:
    path = tmp_path / "balances.json"
    path.write_text(json.dumps({"alice": 100, "bob": 100}))
    result = subprocess.run([
        sys.executable, "-m", "labs.storage.wal.baseline", str(path), "--crash",
    ], check=False)
    assert result.returncode == 73
    assert json.loads(path.read_text()) == {"alice": 90, "bob": 100}


def test_normal_transfer_preserves_total(tmp_path: Path) -> None:
    path = tmp_path / "balances.json"
    path.write_text(json.dumps({"alice": 100, "bob": 100}))
    subprocess.run([
        sys.executable, "-m", "labs.storage.wal.baseline", str(path),
    ], check=True)
    assert json.loads(path.read_text()) == {"alice": 90, "bob": 110}
