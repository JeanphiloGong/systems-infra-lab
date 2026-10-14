"""Replay authored checkpoint fences independently from evolving source files."""

import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PYTHON = str(ROOT / ".venv/bin/python")


def checkpoints(text: str) -> list[tuple[str, str]]:
    return re.findall(r"<!-- checkpoint: ([^ ]+) -->\s*```python\n(.*?)\n```", text, re.S)


def execute(directory: Path, command: str) -> None:
    command = command.replace("uv run python", PYTHON)
    subprocess.run(command, shell=True, executable="/bin/bash", cwd=directory, check=True)


for version in range(1, 5):
    document = ROOT / f"tutorials/01-storage-engines/01-pages-and-locality/v{version}/tutorial.md"
    content = document.read_text()
    with tempfile.TemporaryDirectory(prefix=f"s01-v{version}-review-") as directory:
        working = Path(directory)
        for relative, body in checkpoints(content):
            target = working / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body + "\n")
        for command in re.findall(r"```bash\n(.*?)\n```", content, re.S):
            execute(working, command)
    print(f"S01 v{version} sha256=" + hashlib.sha256(content.encode()).hexdigest(), flush=True)

base = (ROOT / "tutorials/02-transactions-isolation/01-isolation/v0/tutorial.md").read_text()
schema = re.search(r"```sql\n(.*?)\n```", base, re.S).group(1)
for version in (1, 2):
    document = ROOT / f"tutorials/02-transactions-isolation/01-isolation/v{version}/tutorial.md"
    content = document.read_text()
    with tempfile.TemporaryDirectory(prefix=f"t01-v{version}-review-") as directory:
        working = Path(directory)
        for relative, body in checkpoints(base) + checkpoints(content):
            target = working / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body + "\n")
        (working / "labs/transactions/isolation/schema.sql").write_text(schema + "\n")
        for command in re.findall(r"```bash\n(.*?)\n```", content, re.S):
            for line in command.splitlines():
                if "pytest" not in line:
                    execute(working, line)
        if version == 1:
            blocks = re.findall(r"```python\n(.*?)\n```", content, re.S)
            (working / "labs/transactions/isolation/observations.py").write_text(blocks[0] + "\n")
            for level in ("READ COMMITTED", "READ UNCOMMITTED"):
                (working / "check_t01.py").write_text(blocks[1].replace('"READ COMMITTED"', repr(level)) + "\n")
                execute(working, "uv run python check_t01.py")
        else:
            previous = (ROOT / "tutorials/02-transactions-isolation/01-isolation/v1/tutorial.md").read_text()
            previous_code = checkpoints(previous)[0][1]
            function = re.findall(r"```python\n(.*?)\n```", content, re.S)[0]
            patched = previous_code.replace("def main()", function + "\n\ndef main()")
            patched = patched.replace("from psycopg import sql", "from psycopg import sql\nfrom labs.transactions.isolation.transfer import transfer")
            patched = patched.replace("print(dirty_read(writer, reader, args.level))", "print(read_skew(writer, reader, args.level))")
            target = working / "labs/transactions/isolation/observations.py"
            target.write_text(patched + "\n")
            execute(working, "uv run python -m labs.transactions.isolation.observations --level 'READ COMMITTED'")
            patched = patched.replace('choices=["READ COMMITTED", "READ UNCOMMITTED"]', 'choices=["READ COMMITTED", "READ UNCOMMITTED", "REPEATABLE READ"]')
            target.write_text(patched + "\n")
            execute(working, "uv run python -m labs.transactions.isolation.observations --level 'REPEATABLE READ'")
    print(f"T01 v{version} sha256=" + hashlib.sha256(content.encode()).hexdigest(), flush=True)
