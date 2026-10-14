import ast
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


@pytest.mark.parametrize("version,arguments", [(1, []), (2, ["--retry"]), (3, ["--metrics"])])
def test_printed_checkpoint_in_isolation(tmp_path: Path, version: int, arguments: list[str]) -> None:
    guide = Path(f"tutorials/02-transactions-isolation/04-serializability/v{version}/tutorial.md")
    document = guide.read_text()
    sources = [code for code in re.findall(r"```python\n(.*?)\n```", document, re.S)
               if "def main(" in code]
    schemas = re.findall(r"```sql\n(.*?)\n```", document, re.S)
    assert len(sources) == len(schemas) == 1
    assert ("def concurrent_retry(" in sources[0]) == (version >= 2)
    assert ("def measure_once(" in sources[0]) == (version == 3)
    (tmp_path / "serializable.py").write_text(sources[0])
    (tmp_path / "schema.sql").write_text(schemas[0])
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", str(tmp_path / "serializable.py"), *arguments],
        cwd=tmp_path, env=env, text=True, capture_output=True, timeout=40,
    )
    assert result.returncode == 0, result.stderr
    output = ast.literal_eval(result.stdout.strip())
    if version == 1:
        assert output == (1, 1)
    elif version == 2:
        assert sorted(allowed for _, allowed in output) == [False, True]
        assert sum(retries for retries, _ in output) >= 1
        assert all(not allowed for retries, allowed in output if retries)
    else:
        assert output["operations"] == output["committed"] == 20
        assert output["aborted_attempts"] == output["retries"] >= 10
        assert output["allowed"] == output["refused"] == 10
        assert output["remaining"] == 1
        assert output["operations_per_second"] > 0
