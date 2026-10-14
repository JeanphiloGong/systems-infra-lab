from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


GUIDES = Path(__file__).resolve().parents[3] / "tutorials/05-replication/01-leader-follower"
TARGETS = {version: f"labs/replication/leader_follower/v{version}.py" for version in range(5)}


def source(version: int) -> str:
    text = (GUIDES / f"v{version}/tutorial.md").resolve().read_text()
    marker = f"<!-- checkpoint: {TARGETS[version]} -->"
    match = re.search(re.escape(marker) + r"\s*\n```python\n(.*?)```", text, re.S)
    assert match is not None
    return match.group(1)


@pytest.mark.parametrize("version", range(5))
def test_exact_tutorial_checkpoint_executes(version: int, tmp_path: Path) -> None:
    target = tmp_path / f"v{version}.py"
    target.write_text(source(version))
    result = subprocess.run([sys.executable, str(target)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr


def test_each_version_has_one_exact_source_fence() -> None:
    for version in range(5):
        text = (GUIDES / f"v{version}/tutorial.md").resolve().read_text()
        assert text.count("<!-- checkpoint:") == 1
        assert TARGETS[version] in text
