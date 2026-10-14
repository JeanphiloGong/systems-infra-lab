import json
import os
from pathlib import Path
import re
import subprocess
import sys


def test_native_io_deadline_from_complete_fences(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    text = (root / "tutorials/02-traffic/03-retry/v2/tutorial.md").read_text()
    for name in ("v2.py", "io_deadline.py"):
        relative = "labs/traffic/resilience/" + name
        pattern = re.escape(f"<!-- checkpoint: {relative} -->") + r"\s*```python\n(.*?)```"
        blocks = re.findall(pattern, text, re.S)
        assert len(blocks) == 1
        assert blocks[0].rstrip() == (root / relative).read_text().rstrip()
        (tmp_path / name).write_text(blocks[0])
    result = subprocess.run([sys.executable, str(tmp_path / "io_deadline.py")], cwd=tmp_path,
                            env={**os.environ, "PYTHONPATH": str(tmp_path)},
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    measured = json.loads(result.stdout)
    assert measured["attempts"] == 1 and measured["timed_out"] and measured["thread_stopped"]
    assert measured["budget_seconds"] * 0.8 <= measured["elapsed_seconds"] < 1.0
