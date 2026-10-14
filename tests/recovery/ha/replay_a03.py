from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "tutorials/09-recovery/03-failover"


def run(version: int):
    text = (BASE / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\s*```python\n(.*?)\n```", text, re.S)
    selected = {name: code for name, code in blocks if Path(name).name in {"model.py", "experiment.py"}}
    expected_names = {"model.py", "experiment.py"} if version < 2 else {"labs/recovery/ha/model.py", "labs/recovery/ha/experiment.py"}
    assert set(selected) == expected_names
    with tempfile.TemporaryDirectory() as folder:
        directory = Path(folder)
        for name, code in selected.items():
            if version >= 2:
                source = ROOT / name
                assert code.rstrip() == source.read_text().rstrip()
            (directory / Path(name).name).write_text(code + "\n")
        result = subprocess.run([sys.executable, "experiment.py", str(version)], cwd=directory,
                                check=True, capture_output=True, text=True)
        observed = json.loads(result.stdout)
        expected = {
            0: {"rpo_rows": {"order": "one"}, "rto_window": 3},
            1: {"confirmed": {"order": "two"}, "primary": "b"},
            2: {"automatic_primary": "b", "generation": 2},
            3: {"new_value": "two", "old_primary_fenced": True},
            4: {"cutover_primary": "a", "rows": {"order": "three"}},
        }[version]
        assert observed == expected
        return observed


if __name__ == "__main__":
    for version in range(5):
        print(f"v{version} replay ok: {run(version)}")
