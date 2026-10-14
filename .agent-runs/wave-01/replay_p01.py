"""Rebuild each P01 printed checkpoint and execute its printed shell checks."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "tutorials/03-partitioning-scaling/01-routing"

for version in range(4):
    document = TUTORIALS / f"v{version}/tutorial.md"
    text = document.read_text()
    with tempfile.TemporaryDirectory(prefix=f"p01-v{version}-") as directory:
        for relative, code in re.findall(
            r"<!-- checkpoint: ([^ ]+) -->\n```python\n(.*?)\n```", text, re.S
        ):
            target = Path(directory) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code + "\n")
        for command in re.findall(r"```bash\n(.*?)\n```", text, re.S):
            subprocess.run(
                command.replace("uv run python", sys.executable),
                shell=True,
                executable="/bin/bash",
                cwd=directory,
                check=True,
                timeout=30,
            )
    print(f"P01 v{version} replay passed", flush=True)
