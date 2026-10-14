"""Replay T02 v0 intermediate patches and assembled checkpoint."""

import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
document = ROOT / "tutorials/02-transactions-isolation/02-mvcc/v0/tutorial.md"
content = document.read_text()
v1 = (ROOT / "tutorials/02-transactions-isolation/01-isolation/v1/tutorial.md").read_text()
setup = re.findall(r"```python\n(.*?)\n```", v1, re.S)[1]
setup = setup.replace("from labs.transactions.isolation.observations import dirty_read\n", "")
setup = setup.replace('"t01_"', '"t02_"').replace("labs/transactions/isolation/schema.sql", "labs/transactions/mvcc/schema.sql")
patch = re.findall(r"```python\n(.*?)\n```", content, re.S)[0]
start = setup.index("        result = dirty_read")
stop = setup.index("    finally:", start)
setup = setup[:start] + patch + "\n" + setup[stop:]

with tempfile.TemporaryDirectory(prefix="t02-v0-review-") as directory:
    working = Path(directory)
    target = working / "labs/transactions/mvcc/snapshots.py"
    target.parent.mkdir(parents=True)
    target.with_name("schema.sql").write_text(re.search(r"```sql\n(.*?)\n```", content, re.S).group(1) + "\n")

    def run(arguments: list[str], expected: str) -> None:
        result = subprocess.run([str(ROOT / ".venv/bin/python"), *arguments], cwd=working,
                                capture_output=True, text=True, check=True)
        assert expected in result.stdout, result.stdout
        print(result.stdout.strip())

    (working / "check_t02.py").write_text(setup + "\n")
    run(["check_t02.py"], "True True False")
    line = '            first = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]\n'
    late = setup.replace(line, "").replace('            second =', line + '            second =')
    late = late.replace("(True, True, False)", "(False, False, False)")
    (working / "check_t02.py").write_text(late + "\n")
    run(["check_t02.py"], "False False False")
    target.write_text(re.search(r"<!-- checkpoint: [^ ]+ -->\s*```python\n(.*?)\n```", content, re.S).group(1) + "\n")
    run(["-m", "labs.transactions.mvcc.snapshots", "--early-read"], "(True, True, False)")
    run(["-m", "labs.transactions.mvcc.snapshots"], "(False, False, False)")
print("sha256=" + hashlib.sha256(content.encode()).hexdigest())
