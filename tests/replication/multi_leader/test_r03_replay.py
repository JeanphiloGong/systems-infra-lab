from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/05-replication/03-multi-leader"
DEPENDENCIES = {0: ["v0.py"], 1: ["v0.py", "v1.py"], 2: ["v0.py", "v2.py"], 3: ["v3.py"], 4: ["v0.py", "v2.py", "v4.py"]}


@pytest.mark.parametrize("version", range(5))
def test_full_tutorial_sources_and_checks(version: int, tmp_path: Path) -> None:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    sources = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
    expected = [f"labs/replication/multi_leader/{name}" for name in DEPENDENCIES[version]]
    assert [path for path, _ in sources] == expected
    for path, code in sources:
        assert code + "\n" == (ROOT / path).read_text(), f"source drift: {path}"
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(code + "\n")
    directory = tmp_path / "labs/replication/multi_leader"
    checks = re.findall(r"<!-- check: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
    assert [name for name, _ in checks] == [f"check_v{version}.py"]
    for name, code in checks:
        (directory / name).write_text(code + "\n")
    # Execute both the printed entry point and the printed semantic checks.
    for name in (f"v{version}.py", f"check_v{version}.py"):
        result = subprocess.run([sys.executable, str(directory / name)], cwd=tmp_path,
                                env={**os.environ, "PYTHONPATH": str(tmp_path)},
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        if name.startswith("check_"):
            assert f"v{version}:" in result.stdout and "passed" in result.stdout
