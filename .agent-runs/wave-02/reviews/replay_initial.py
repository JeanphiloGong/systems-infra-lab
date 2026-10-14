"""Independent replay of revised S02 v0-v4 and T03 v0-v1."""

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
    with tempfile.TemporaryDirectory(prefix="s02-review-") as directory:
        working = Path(directory)
        for relative, body in re.findall(PATTERN, text, re.S):
            target = working / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body + "\n")
        commands = re.findall(r"```bash\n(.*?)\n```", text, re.S)
        assert commands
        for command in commands:
            subprocess.run(command.replace("uv run python", PYTHON), shell=True,
                           executable="/bin/bash", cwd=working, check=True)
    print(f"S02 v{version} sha256=" + hashlib.sha256(text.encode()).hexdigest(), flush=True)

v0 = (ROOT / "tutorials/02-transactions-isolation/03-locking/v0/tutorial.md").read_text()
schema = re.search(r"```sql\n(.*?)\n```", v0, re.S).group(1)
for version in (0, 1):
    document = ROOT / f"tutorials/02-transactions-isolation/03-locking/v{version}/tutorial.md"
    text = document.read_text()
    with tempfile.TemporaryDirectory(prefix="t03-review-") as directory:
        working = Path(directory)
        relative, body = re.findall(PATTERN, text, re.S)[0]
        target = working / relative
        target.parent.mkdir(parents=True)
        target.write_text(body + "\n")
        target.with_name("schema.sql").write_text(schema + "\n")
        arguments = ["--optimistic"] if version else []

        def run(expected: str) -> None:
            result = subprocess.run([PYTHON, "-m", "labs.transactions.locking.locking", *arguments],
                                    cwd=working, capture_output=True, text=True, check=True)
            assert expected in result.stdout, result.stdout
            print(result.stdout.strip())

        run("(1, 0)" if version else "(10, 10, 9)")
        if version == 0:
            b = '    b = second.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0]\n'
            update = '    first.execute("UPDATE inventory SET quantity=%s WHERE id=1", (a - 1,))\n'
            target.write_text(body.replace(b, "").replace(update, update + b) + "\n")
            run("(10, 9, 8)")
        else:
            initialize = '            first.execute(Path(__file__).with_name("schema.sql").read_text())\n'
            target.write_text(body.replace(initialize, initialize + '            first.execute("UPDATE inventory SET quantity=0 WHERE id=1")\n') + "\n")
            run("(0, 0)")
    print(f"T03 v{version} sha256=" + hashlib.sha256(text.encode()).hexdigest(), flush=True)
