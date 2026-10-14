from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import psycopg
import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/07-coordination/03-distributed-commit"


def extract(version: int, destination: Path) -> Path:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
    names = ["pg.py", f"v{version}.py"] if version < 3 else (["v3.py"] if version == 3 else ["v3.py", "v4.py"])
    assert [name for name, _ in blocks] == ["labs/coordination/commit/" + name for name in names]
    for relative, code in blocks:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code + "\n")
        assert code + "\n" == (ROOT / relative).read_text(), f"fence drift: {relative}"
    return destination / f"labs/coordination/commit/v{version}.py"


def execute(script: Path, cwd: Path, arguments: tuple[str, ...] = ()) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, str(script), *arguments], cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(cwd)},
        capture_output=True, text=True, timeout=45,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("version,arguments", [(0, ()), (1, ()), (2, ("commit",)), (2, ("abort",)), (2, ("missing",)), (2, ("commit", "--partial"))])
def test_actual_postgres_from_tutorial(version: int, arguments: tuple[str, ...], tmp_path: Path) -> None:
    assert "D03_DATABASE_URL" in os.environ, "Configure the disposable PostgreSQL server described in the D03 README"
    script = extract(version, tmp_path)
    result = execute(script, tmp_path, arguments)
    if version == 0:
        assert result == {"balances": [70, 100], "total": 170}
    elif version == 1:
        assert result == {"before": [100, 100], "prepared": 2, "after": [70, 130]}
    else:
        committed = arguments[0] == "commit"
        partial = "--partial" in arguments
        assert result["after"] == ([70, 130] if committed else [100, 100])
        assert result["before"] == ([70, 100] if partial else [100, 100])
        assert result["pending"] == (1 if partial else 2)
        assert result["locked"] == ([False, True] if partial else [True, True])
        assert result["resolved"] == ("commit" if committed else "abort")


def test_three_phase_trace_and_partition_counterexample(tmp_path: Path) -> None:
    for version in (3, 4):
        script = extract(version, tmp_path)
        result = execute(script, tmp_path)
        if version == 3:
            assert result == {"history": [["ready", "ready"], ["precommit", "precommit"], ["committed", "committed"]], "messages_3pc": 12, "messages_2pc": 8}
        else:
            assert result == {"before": ["precommit", "ready"], "after": ["committed", "aborted"], "atomic": False, "safe_action_under_unknown_delay": "block"}


def test_durable_decision_cannot_flip_and_phase_cannot_skip(tmp_path: Path) -> None:
    script = extract(2, tmp_path)
    extract(3, tmp_path)
    check = '''
from pathlib import Path
from v2 import record_decision, recover
from v3 import Participant
path = Path("decision.sqlite")
assert recover([], [], Path("missing.sqlite")) == "in_doubt"
record_decision(path, "commit")
record_decision(path, "commit")
try:
    record_decision(path, "abort")
except ValueError:
    pass
else:
    raise AssertionError("durable decision flipped")
participant = Participant()
participant.receive("prepare")
try:
    participant.receive("commit")
except ValueError:
    pass
else:
    raise AssertionError("precommit was skipped")
'''
    result = subprocess.run([sys.executable, "-c", check], cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(script.parent)}, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_server_capacity_and_prepared_cleanup() -> None:
    with psycopg.connect(os.environ["D03_DATABASE_URL"], autocommit=True) as conn:
        assert int(conn.execute("SHOW max_prepared_transactions").fetchone()[0]) >= 2
        assert conn.execute("SELECT count(*) FROM pg_prepared_xacts WHERE gid LIKE 'd03_%'").fetchone()[0] == 0
