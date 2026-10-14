from __future__ import annotations

import re
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/06-consensus/01-cap-quorum"
TARGETS = {version: f"labs/consensus/cap_quorum/v{version}.py" for version in range(4)}


def source(version: int) -> str:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    marker = f"<!-- checkpoint: {TARGETS[version]} -->"
    match = re.search(re.escape(marker) + r"\s*\n```python\n(.*?)```", text, re.S)
    assert match is not None
    return match.group(1)


@pytest.mark.parametrize("version", range(4))
def test_exact_checkpoint_executes(version: int, tmp_path: Path) -> None:
    target = tmp_path / f"v{version}.py"
    target.write_text(source(version))
    result = subprocess.run([sys.executable, str(target)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert source(version).rstrip() == (ROOT / TARGETS[version]).read_text().rstrip()
    if version == 3:
        observed = json.loads(result.stdout)
        assert observed['intersection'] is True
        assert observed['reads'] == [[1, 'new'], [0, 'old']]
        assert observed['write_acks'] == 2
        assert observed['trace'].index('return read1(new)') < observed['trace'].index('invoke read2(b,c)')
        assert observed['trace'][-1] == 'return write(success)'


def test_each_tutorial_has_one_exact_fence() -> None:
    for version, target in TARGETS.items():
        text = (GUIDES / f"v{version}/tutorial.md").read_text()
        assert text.count("<!-- checkpoint:") == 1
        assert target in text
