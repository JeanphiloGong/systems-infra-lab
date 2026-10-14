"""Independent replay of frozen Wave 02 S02/T03 tutorial checkpoints."""

import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PYTHON = str(ROOT / ".venv/bin/python")
PATTERN = r"<!-- checkpoint: ([^ ]+) -->\s*```python\n(.*?)\n```"

for version in range(5):
    document = ROOT / f"tutorials/01-storage-engines/02-b-plus-tree/v{version}/tutorial.md"
    text = document.read_text()
    if version == 4:
        continue
    with tempfile.TemporaryDirectory(prefix=f"s02-{version}-review-") as directory:
        working = Path(directory)
        for relative, body in re.findall(PATTERN, text, re.S):
            target = working / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body + "\n")
        for command in re.findall(r"```bash\n(.*?)\n```", text, re.S):
            if "pytest" not in command:
                subprocess.run(command.replace("uv run python", PYTHON), shell=True,
                               executable="/bin/bash", cwd=working, check=True)
    print(f"S02v{version} sha256=" + hashlib.sha256(text.encode()).hexdigest(), flush=True)

for version, module, expected in ((0, "labs.transactions.locking.locking", "(10, 10, 9)"),
                                  (1, "labs.transactions.locking.locking", "(1, 0)"),
                                  (2, "labs.transactions.locking.row_lock", "quantity=8"),
                                  (3, "labs.transactions.locking.deadlock", "victims and retried quantities: (1,8,8)"),
                                  (4, "labs.transactions.locking.escalation", "records_before=3")):
    document = ROOT / f"tutorials/02-transactions-isolation/03-locking/v{version}/tutorial.md"
    text = document.read_text()
    with tempfile.TemporaryDirectory(prefix=f"t03-{version}-review-") as directory:
        working = Path(directory)
        for relative, body in re.findall(PATTERN, text, re.S):
            target = working / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body + "\n")
        sql_blocks = re.findall(r"```sql\n(.*?)\n```", text, re.S)
        if sql_blocks:
            target = working / "labs/transactions/locking/schema.sql"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(sql_blocks[-1] + "\n")
        args = ["--optimistic"] if version == 1 else []
        result = subprocess.run([PYTHON, "-m", module, *args], cwd=working,
                                capture_output=True, text=True,
                                env={**__import__("os").environ,
                                     "SYSTEMS_LAB_DATABASE_URL": "postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab"},
                                check=True)
        assert expected in result.stdout, result.stdout
        print(result.stdout.strip())
    print(f"T03v{version} sha256=" + hashlib.sha256(text.encode()).hexdigest(), flush=True)

document = ROOT / "tutorials/01-storage-engines/02-b-plus-tree/v5/tutorial.md"
text = document.read_text()
print("S02v5 sha256=" + hashlib.sha256(text.encode()).hexdigest())
