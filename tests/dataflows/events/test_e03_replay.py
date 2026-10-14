from pathlib import Path
import json
import os
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/08-dataflows/03-events"
DEPS = {0: ["v0.py"], 1: ["v1.py"], 2: ["v2.py"], 3: ["v3.py"], 4: ["v4.py"]}


@pytest.mark.parametrize("version", range(5))
def test_exact_fence_replay(version, tmp_path):
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
    assert [Path(path).name for path, _ in blocks] == DEPS[version]
    for path, code in blocks:
        assert code + "\n" == (ROOT / path).read_text()
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code + "\n")
    result = subprocess.run([sys.executable, str(tmp_path / f"labs/dataflows/events/v{version}.py")], cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path)}, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    if version == 0: assert output["history_available"] is False
    if version == 1: assert output["invalid_rejected"] and output["versions"] == [1, 2, 3]
    if version == 2: assert output == {"versions": [1, 2], "conflict": True}
    if version == 3: assert output["applied"] == 3 and not output["duplicate_applied"] and output["out_of_order_rejected"] and tuple(output["lagged_after_rebuild"]) == ("shipped", 3)
    if version == 4: assert output["upcast_currency"] == "USD" and output["rebuild_side_effects"] == 0 and output["new_event_effects"] == 1
