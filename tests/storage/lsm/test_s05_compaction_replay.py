from pathlib import Path
import os
import re
import subprocess
import sys


def test_complete_checkpoint_and_naive_break(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    text = (root / "tutorials/01-storage-engines/05-lsm/v4/tutorial.md").read_text()
    package = tmp_path / "labs/storage/lsm"
    package.mkdir(parents=True)
    for name in ("sstable", "tombstones", "compaction"):
        marker = f"<!-- checkpoint: labs/storage/lsm/{name}.py -->"
        match = re.search(re.escape(marker) + r"\s*```python\n(.*?)```", text, re.S)
        assert match is not None
        (package / f"{name}.py").write_text(match.group(1))
    env = {**os.environ, "PYTHONPATH": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1"}
    naive = re.findall(r"```python\n(.*?)```", text, re.S)[0]
    broken = subprocess.run([sys.executable, "-c", naive], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=5)
    assert broken.returncode == 0, broken.stderr
    assert broken.stdout.strip() == "premature drop resurrects: old"
    directory = tmp_path / "data"
    directory.mkdir()
    command = [sys.executable, "-m", "labs.storage.lsm.compaction", str(directory)]
    for flags in (["--create"], []):
        result = subprocess.run(command + flags, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=5)
        assert result.returncode == 0, result.stderr
        assert result.stdout == 'partial: None ["delete"]\nfull: None None\nkeep: new\n'
