"""Run exactly the complete sources printed in each chapter, with no repo imports."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/02-traffic/04-herd"
DEPENDENCIES = {0: [0], 1: [0, 1], 2: [0, 2], 3: [0, 2, 3]}


@pytest.mark.parametrize("version", range(4))
def test_complete_extracted_experiment(version, tmp_path):
    document = (GUIDES / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", document, re.S)
    expected = [f"labs/traffic/herd/v{v}.py" for v in DEPENDENCIES[version]]
    assert [name for name, _ in blocks] == expected
    for name, code in blocks:
        assert code + "\n" == (ROOT / name).read_text()
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code + "\n")
    result = subprocess.run(
        [sys.executable, str(tmp_path / f"labs/traffic/herd/v{version}.py")],
        cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "Task was destroyed" not in result.stderr
    observed = json.loads(result.stdout)
    if version == 0:
        assert observed["peak"] == observed["origin_calls"] == 20
    elif version == 1:
        assert observed["same_key_calls"] == 1 and observed["distinct_key_calls"] == 2
    elif version == 2:
        assert observed["cancelled_waiter_isolated"] and observed["timed_out_waiter_isolated"]
        assert observed["failure_fanout"] == observed["fill_timeout_calls"] == 1
    else:
        assert observed["synchronized"]["peak"] > observed["jittered"]["peak"]
        assert observed["per_process_fills"] == [1, 1]
