"""Independent follow-up review replays for S03 and T02."""

import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PYTHON = str(ROOT / ".venv/bin/python")
PATTERN = r"<!-- checkpoint: ([^ ]+) -->\s*```python\n(.*?)\n```"


def run(working: Path, script: str) -> None:
    subprocess.run(script.replace("uv run python", PYTHON), shell=True,
                   executable="/bin/bash", cwd=working, check=True)


for version in (3, 4):
    document = ROOT / f"tutorials/01-storage-engines/03-wal-and-recovery/v{version}/tutorial.md"
    text = document.read_text()
    with tempfile.TemporaryDirectory(prefix="s03-followup-") as directory:
        working = Path(directory)
        for relative, body in re.findall(PATTERN, text, re.S):
            target = working / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body + "\n")
        for command in re.findall(r"```bash\n(.*?)\n```", text, re.S):
            run(working, command)
    print(f"S03v{version} sha256=" + hashlib.sha256(text.encode()).hexdigest(), flush=True)

prefix = ROOT / "tutorials/02-transactions-isolation/02-mvcc"
docs = [(prefix / f"v{version}/tutorial.md").read_text() for version in range(4)]
t01 = (ROOT / "tutorials/02-transactions-isolation/01-isolation/v1/tutorial.md").read_text()
setup = re.findall(r"```python\n(.*?)\n```", t01, re.S)[1]
setup = setup.replace("from labs.transactions.isolation.observations import dirty_read\n", "")
setup = setup.replace('"t01_"', '"t02_"').replace("labs/transactions/isolation/schema.sql", "labs/transactions/mvcc/schema.sql")
start, stop = setup.index("        result = dirty_read"), setup.index("    finally:")

with tempfile.TemporaryDirectory(prefix="t02-followup-") as directory:
    working = Path(directory)
    for text in docs:
        for relative, body in re.findall(PATTERN, text, re.S):
            target = working / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body + "\n")
    module = working / "labs/transactions/mvcc"
    for version, filename in ((0, "schema.sql"), (3, "guard.sql")):
        (module / filename).write_text(re.search(r"```sql\n(.*?)\n```", docs[version], re.S).group(1) + "\n")
    for version in (1, 2, 3):
        for command in re.findall(r"```bash\n(.*?)\n```", docs[version], re.S):
            run(working, "\n".join(line for line in command.splitlines() if "pytest" not in line))
    v2blocks = re.findall(r"```python\n(.*?)\n```", docs[2], re.S)
    for body in v2blocks[:2]:
        (working / "check_t02.py").write_text(setup[:start] + body + "\n" + setup[stop:])
        run(working, "uv run python check_t02.py")
    v3blocks = re.findall(r"```python\n(.*?)\n```", docs[3], re.S)
    conflict = next(body for body in v3blocks if "conflicted = False" in body)
    retry = next(body for body in v3blocks if "assert allowed is False" in body)
    load_guard = '        writer.execute(Path("labs/transactions/mvcc/guard.sql").read_text())\n'
    for body in (conflict, conflict + "\n" + retry):
        (working / "check_t02.py").write_text(setup[:start] + load_guard + body + "\n" + setup[stop:])
        run(working, "uv run python check_t02.py")
    print("T02 intermediate patches passed")
for version in (1, 2, 3):
    print(f"T02v{version} sha256=" + hashlib.sha256(docs[version].encode()).hexdigest())
