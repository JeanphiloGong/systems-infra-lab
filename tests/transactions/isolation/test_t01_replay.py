import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/02-transactions-isolation/01-isolation"


def checkpoint(version: int, name: str) -> str:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    marker = f"<!-- checkpoint: labs/transactions/isolation/{name} -->"
    match = re.search(re.escape(marker) + r"\s*```python\n(.*?)```", text, re.S)
    assert match is not None
    return match.group(1)


@pytest.mark.parametrize("version", range(5))
def test_frozen_tutorial_checkpoint(tmp_path: Path, version: int) -> None:
    target = tmp_path / "labs/transactions/isolation"
    target.mkdir(parents=True)
    guide = (GUIDES / "v0/tutorial.md").read_text()
    schema = re.search(r"```sql\n(.*?)```", guide, re.S)
    assert schema is not None
    (target / "schema.sql").write_text(schema.group(1))
    (target / "transfer.py").write_text(checkpoint(0, "transfer.py"))
    cases: list[tuple[str, list[str], str, int]] = [
        ("transfer", [], "[(1, 70), (2, 130)]", 0),
        ("transfer", ["--fail-after-debit"], "[(1, 100), (2, 100)]", 1),
    ]
    if version in {1, 2, 3}:
        (target / "observations.py").write_text(checkpoint(version, "observations.py"))
        for level in ("READ COMMITTED", "READ UNCOMMITTED"):
            cases.append(("observations", ["--level", level], "(70, 100, 100)", 0))
        if version >= 2:
            for level, expected in [("READ COMMITTED", "(100, 130, 200)"), ("REPEATABLE READ", "(100, 100, 200)")]:
                cases.append(("observations", ["--scenario", "skew", "--level", level], expected, 0))
        if version >= 3:
            for level, expected in [("READ COMMITTED", "(2, 3, 3)"), ("REPEATABLE READ", "(2, 2, 3)")]:
                cases.append(("observations", ["--scenario", "phantom", "--level", level], expected, 0))
    if version == 4:
        (target / "acid.py").write_text(checkpoint(4, "acid.py"))
        cases.append(("acid", [], "constraint, business total: (200, 199)\nafter reconnect: [(70,), (130,)]", 0))
    for module, args, expected, status in cases:
        result = subprocess.run(
            [sys.executable, "-m", f"labs.transactions.isolation.{module}", *args],
            cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path)},
            capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == status, result.stderr
        assert result.stdout.strip() == expected
