import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def test_printed_dependencies_and_actual_cli_sequence(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    text = (root / "tutorials/01-storage-engines/05-lsm/v5/tutorial.md").read_text()
    package = tmp_path / "labs/storage/lsm"
    package.mkdir(parents=True)
    for parent in (tmp_path/"labs", tmp_path/"labs/storage", package):
        (parent/"__init__.py").write_text("")
    for name in ("sstable","tombstones","manifest"):
        marker = f"<!-- checkpoint: labs/storage/lsm/{name}.py -->"
        match = re.search(re.escape(marker) + r"\s*```python\n(.*?)```", text, re.S)
        assert match is not None
        (package/f"{name}.py").write_text(match.group(1))
    env = {**os.environ,"PYTHONPATH":str(tmp_path),"PYTHONDONTWRITEBYTECODE":"1"}
    naive = re.findall(r"```python\n(.*?)```",text,re.S)[0]
    baseline = subprocess.run([sys.executable,"-c",naive],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
    assert baseline.returncode == 0, baseline.stderr
    assert baseline.stdout.strip() == "partial manifest is unreadable"
    directory = tmp_path/"data"
    directory.mkdir()
    commands = [line for line in text.splitlines() if line.startswith("uv run python -m labs.storage.lsm.manifest ")]
    assert len(commands) == 6
    for line in commands:
        words = shlex.split(line.replace('$manifest_demo_dir',str(directory)))
        command = [sys.executable,*words[3:]]
        result = subprocess.run(command,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
        if "--crash" in words:
            before = words[-1] == "before_publish"
            assert result.returncode == (71 if before else 72), result.stderr
            assert result.stdout == ""
            assert json.loads((directory/"MANIFEST").read_text()) == (["old.sst"] if before else ["new.sst","old.sst"])
            assert (directory/"MANIFEST.tmp").exists() == before
        else:
            assert result.returncode == 0, result.stderr
            names = json.loads((directory/"MANIFEST").read_text())
            expected = "old" if names == ["old.sst"] else "new"
            assert json.loads(result.stdout) == {"k":expected,"stable":"yes"}
    assert not (directory/"MANIFEST.tmp").exists()
