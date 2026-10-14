from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/07-coordination/04-saga"


@pytest.mark.parametrize("version", range(5))
def test_exact_fence_replay(version: int, tmp_path: Path) -> None:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    marker = f"<!-- checkpoint: labs/coordination/saga/v{version}.py -->"
    match = re.search(re.escape(marker) + r"\s*\n```python\n(.*?)```", text, re.S)
    assert match is not None
    source = match.group(1)
    assert source.rstrip() == (ROOT / f"labs/coordination/saga/v{version}.py").read_text().rstrip()
    target = tmp_path / f"v{version}.py"
    target.write_text(source)
    result = subprocess.run([sys.executable, str(target)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
