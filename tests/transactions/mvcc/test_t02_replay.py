import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/02-transactions-isolation/02-mvcc"


@pytest.mark.parametrize("version,module,args,expected", [
    (0,"snapshots",["--early-read"],"(True, True, False)"),
    (0,"snapshots",[],"(False, False, False)"),
    (1,"model",[],"True False"),
    (2,"write_skew",[],"(2, 2, 0)"),
    (3,"protected",[],"(1, False, 1)"),
])
def test_t02_document_checkpoint(tmp_path: Path, version: int, module: str, args: list[str], expected: str) -> None:
    target = tmp_path / "labs/transactions/mvcc"
    target.mkdir(parents=True)
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    marker = f"<!-- checkpoint: labs/transactions/mvcc/{module}.py -->"
    code = re.search(re.escape(marker) + r"\s*```python\n(.*?)```", text, re.S)
    assert code is not None
    (target / f"{module}.py").write_text(code.group(1))
    schema = re.search(r"```sql\n(.*?)```", (GUIDES / "v0/tutorial.md").read_text(), re.S)
    assert schema is not None
    (target / "schema.sql").write_text(schema.group(1))
    if version == 3:
        guard = re.search(r"```sql\n(.*?)```", text, re.S)
        assert guard is not None
        (target / "guard.sql").write_text(guard.group(1))
    result = subprocess.run(
        [sys.executable, "-m", f"labs.transactions.mvcc.{module}", *args],
        cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@pytest.mark.parametrize("stage", ["serial", "skew", "conflict", "retry"])
def test_t02_intermediate_replacements(stage: str) -> None:
    t01 = ROOT / "tutorials/02-transactions-isolation/01-isolation/v1/tutorial.md"
    blocks = re.findall(r"```python\n(.*?)```", t01.read_text(), re.S)
    base = next(block for block in blocks if "dsn = os.environ" in block and "result = dirty_read" in block)
    base = base.replace("from labs.transactions.isolation.observations import dirty_read\n", "")
    base = base.replace('"t01_"', '"t02_"').replace("transactions/isolation/schema.sql", "transactions/mvcc/schema.sql")
    v2 = re.findall(r"```python\n(.*?)```", (GUIDES / "v2/tutorial.md").read_text(), re.S)
    v3 = re.findall(r"```python\n(.*?)```", (GUIDES / "v3/tutorial.md").read_text(), re.S)
    if stage == "serial":
        experiment = v2[0]
    elif stage == "skew":
        experiment = v2[1]
    else:
        experiment = v3[0] + v3[1]
        if stage == "retry":
            experiment += v3[2]
    start = base.index("        result = dirty_read")
    end = base.index("    finally:", start)
    script = base[:start] + experiment + base[end:]
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
