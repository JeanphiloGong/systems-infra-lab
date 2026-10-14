"""Replay the complete S01 v0 checkpoint and its printed verification script."""

import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
document = ROOT / "tutorials/01-storage-engines/01-pages-and-locality/v0/tutorial.md"
text = document.read_text()
blocks = re.findall(r"```(\w+)\n(.*?)\n```", text, re.S)
checkpoint = next(body for language, body in blocks if language == "python" and "def scan(" in body)
commands = [body for language, body in blocks if language == "bash"]
with tempfile.TemporaryDirectory(prefix="s01-review-") as directory:
    target = Path(directory) / "labs/storage/pages/records.py"
    target.parent.mkdir(parents=True)
    target.write_text(checkpoint + "\n")
    for command in commands:
        subprocess.run(command.replace("uv run python", str(ROOT / ".venv/bin/python")), shell=True,
                       executable="/bin/bash", cwd=directory, check=True)
print("tutorial_sha256=" + hashlib.sha256(document.read_bytes()).hexdigest())
print("checkpoint_sha256=" + hashlib.sha256(checkpoint.encode()).hexdigest())
