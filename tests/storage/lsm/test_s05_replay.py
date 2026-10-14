from pathlib import Path
import re
import subprocess
import sys
import os

import pytest


GUIDES = Path(__file__).resolve().parents[3] / "tutorials/01-storage-engines/05-lsm"


@pytest.mark.parametrize("version,module", [(0, "memtable"), (1, "sstable")])
def test_printed_checkpoint_in_clean_directory(tmp_path: Path, version: int, module: str) -> None:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    marker = f"<!-- checkpoint: labs/storage/lsm/{module}.py -->"
    match = re.search(re.escape(marker) + r"\s*```python\n(.*?)```", text, re.S)
    assert match is not None
    script = tmp_path / f"{module}.py"
    script.write_text(match.group(1))
    args = [] if version == 0 else [str(tmp_path / "one.sst"), "--create"]
    first = subprocess.run([sys.executable, str(script), *args], cwd=tmp_path, capture_output=True, text=True, timeout=5)
    assert first.returncode == 0, first.stderr
    if version == 0:
        assert first.stdout == "[('a', 'first'), ('z', 'new')]\nfresh instance: None\n"
    else:
        reopened = subprocess.run([sys.executable, str(script), str(tmp_path / "one.sst")], cwd=tmp_path, capture_output=True, text=True, timeout=5)
        assert reopened.returncode == 0, reopened.stderr
        assert reopened.stdout == first.stdout == "[('a', 'first'), ('z', 'latest')]\n"


def test_intermediate_examples_execute() -> None:
    for version in (0, 1):
        text = (GUIDES / f"v{version}/tutorial.md").read_text()
        for block in re.findall(r"```python\n(.*?)```", text, re.S)[:-1]:
            result = subprocess.run([sys.executable, "-c", block], capture_output=True, text=True, timeout=5)
            assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("version,module,expected", [
    (2, "versions", "['new', 'yes', '', None]"),
    (3, "tombstones", "[None, 'yes', '__TOMBSTONE__', '', '[\"delete\"]', None]"),
])
def test_multi_file_printed_code_and_fresh_process(tmp_path: Path, version: int, module: str, expected: str) -> None:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    package = tmp_path / "labs/storage/lsm"
    package.mkdir(parents=True)
    for name in ("sstable", module):
        marker = f"<!-- checkpoint: labs/storage/lsm/{name}.py -->"
        match = re.search(re.escape(marker) + r"\s*```python\n(.*?)```", text, re.S)
        assert match is not None
        (package / f"{name}.py").write_text(match.group(1))
    data = tmp_path / "data"
    data.mkdir()
    command = [sys.executable, "-m", f"labs.storage.lsm.{module}", str(data)]
    env = {**os.environ, "PYTHONPATH": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1"}
    for args in (["--create"], []):
        result = subprocess.run(command + args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=5)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == expected
    if version == 2:
        path = package / "versions.py"
        path.write_text(path.read_text().replace("VersionedStore([new, old])", "VersionedStore([old, new])"))
        reversed_order = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=5)
        assert reversed_order.returncode == 0, reversed_order.stderr
        assert reversed_order.stdout.strip() == "['old', 'yes', 'old', None]"


def test_v3_naive_omission_from_printed_v2_baseline(tmp_path: Path) -> None:
    text = (GUIDES / "v2/tutorial.md").read_text()
    package = tmp_path / "labs/storage/lsm"
    package.mkdir(parents=True)
    for name in ("sstable", "versions"):
        marker = f"<!-- checkpoint: labs/storage/lsm/{name}.py -->"
        match = re.search(re.escape(marker) + r"\s*```python\n(.*?)```", text, re.S)
        assert match is not None
        (package / f"{name}.py").write_text(match.group(1))
    naive = re.findall(r"```python\n(.*?)```", (GUIDES / "v3/tutorial.md").read_text(), re.S)[0]
    result = subprocess.run([sys.executable, "-c", naive], cwd=tmp_path,
                            env={**os.environ, "PYTHONPATH": str(tmp_path)},
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "omission resurrects: old"
