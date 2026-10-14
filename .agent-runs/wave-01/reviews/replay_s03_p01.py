"""Replay ready S03 and P01 versions from their printed checkpoint files."""

import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
documents = [
    "tutorials/01-storage-engines/03-wal-and-recovery/v0/tutorial.md",
    "tutorials/01-storage-engines/03-wal-and-recovery/v1/tutorial.md",
    "tutorials/01-storage-engines/03-wal-and-recovery/v2/tutorial.md",
    "tutorials/03-partitioning-scaling/01-routing/v0/tutorial.md",
    "tutorials/03-partitioning-scaling/01-routing/v1/tutorial.md",
    "tutorials/03-partitioning-scaling/01-routing/v2/tutorial.md",
    "tutorials/03-partitioning-scaling/01-routing/v3/tutorial.md",
]

for relative in documents:
    document = ROOT / relative
    content = document.read_text()
    with tempfile.TemporaryDirectory(prefix="checkpoint-review-") as directory:
        for target_name, body in re.findall(r"<!-- checkpoint: ([^ ]+) -->\s*```python\n(.*?)\n```", content, re.S):
            target = Path(directory) / target_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body + "\n")
        for command in re.findall(r"```bash\n(.*?)\n```", content, re.S):
            subprocess.run(command.replace("uv run python", str(ROOT / ".venv/bin/python")),
                           shell=True, executable="/bin/bash", cwd=directory, check=True)
    print(relative, "sha256=" + hashlib.sha256(content.encode()).hexdigest(), flush=True)
