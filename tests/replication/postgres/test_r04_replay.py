from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/05-replication/04-postgres"
TARGETS = {0: ["common.py", "v0.py"], 1: ["common.py", "v1.py"], 2: ["common.py", "v1.py", "v2.py"], 3: ["common.py", "v1.py", "v3.py"]}


def extract(version: int, destination: Path) -> Path:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```(?:python|bash|sql|yaml)\n(.*?)\n```", text, re.S)
    python = {}
    for path, code in blocks:
        source = ROOT / path
        assert source.exists(), path
        assert code.rstrip() == source.read_text().rstrip(), f"fence drift: {path}"
        if path.startswith("labs/replication/postgres/") and path.endswith(".py"):
            python[Path(path).name] = code
    assert list(python) == TARGETS[version]
    package = destination / "labs/replication/postgres"
    package.mkdir(parents=True)
    for name, code in python.items():
        (package / name).write_text(code + "\n")
    (package / "__init__.py").write_text("")
    return package / f"v{version}.py"


@pytest.mark.parametrize("version", range(4))
def test_real_postgres_version_replay(version: int, tmp_path: Path) -> None:
    assert os.environ.get("R04_DATABASE_URL") == "postgresql://r04:r04_local_only@127.0.0.1:55440/r04", "Start infra/r04.compose.yaml and set R04_DATABASE_URL"
    script = extract(version, tmp_path)
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path / "labs/replication/postgres")}, capture_output=True, text=True, timeout=150)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    if version == 0:
        assert output["rows"] == 1 and output["read_only"]
    elif version == 1:
        assert output["rows"] == [[2, "updated"]] and output["unpublished_absent"]
    elif version == 2:
        assert output["physical_ddl"] and not output["logical_ddl_automatic"] and output["identity_rejected"]
    else:
        assert output["retained_bytes"] > output["paused_bytes"] and output["subscriber_rows"] == 20001 and output["recovered_bytes"] < output["retained_bytes"]


def test_all_versions_have_complete_python_fences() -> None:
    for version, expected in TARGETS.items():
        text = (GUIDES / f"v{version}/tutorial.md").read_text()
        paths = [Path(path).name for path, _ in re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)]
        assert paths == expected
