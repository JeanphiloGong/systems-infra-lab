"""Replay T01 v3/v4 intermediate instructions and final checkpoint code."""

import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PREFIX = ROOT / "tutorials/02-transactions-isolation/01-isolation"
docs = [(PREFIX / f"v{version}/tutorial.md").read_text() for version in range(5)]
pattern = r"<!-- checkpoint: ([^ ]+) -->\s*```python\n(.*?)\n```"
schema = re.search(r"```sql\n(.*?)\n```", docs[0], re.S).group(1)

with tempfile.TemporaryDirectory(prefix="t01-later-review-") as directory:
    working = Path(directory)
    for relative, body in re.findall(pattern, docs[0], re.S):
        target = working / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body + "\n")
    (working / "labs/transactions/isolation/schema.sql").write_text(schema + "\n")

    def check(module: str, arguments: list[str], expected: str) -> None:
        result = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", module, *arguments],
                                cwd=working, capture_output=True, text=True, check=True)
        assert expected in result.stdout, result.stdout
        print(arguments, result.stdout.strip())

    function = re.findall(r"```python\n(.*?)\n```", docs[3], re.S)[0]
    previous = re.findall(pattern, docs[2], re.S)[0][1]
    patched = previous.replace("def main()", function + "\n\ndef main()")
    patched = patched.replace("print(read_skew(writer, reader, args.level))", "print(phantom_read(writer, reader, args.level))")
    observations = working / "labs/transactions/isolation/observations.py"
    observations.write_text(patched + "\n")
    for level, expected in (("READ COMMITTED", "(2, 3, 3)"), ("REPEATABLE READ", "(2, 2, 3)")):
        check("labs.transactions.isolation.observations", ["--scenario", "skew", "--level", level], expected)
    observations.write_text(re.findall(pattern, docs[3], re.S)[0][1] + "\n")
    for level, expected in (("READ COMMITTED", "(2, 3, 3)"), ("REPEATABLE READ", "(2, 2, 3)")):
        check("labs.transactions.isolation.observations", ["--scenario", "phantom", "--level", level], expected)

    function = re.findall(r"```python\n(.*?)\n```", docs[4], re.S)[0]
    acid = working / "labs/transactions/isolation/acid.py"
    acid.write_text(function + "\n")
    check_source = re.findall(r"```python\n(.*?)\n```", docs[1], re.S)[1]
    check_source = check_source.replace("from labs.transactions.isolation.observations import dirty_read", "from labs.transactions.isolation.acid import constraint_trace")
    check_source = check_source.replace('dirty_read(writer, reader, "READ COMMITTED")', "constraint_trace(writer)")
    check_source = check_source.replace("assert result == (70, 100, 100)", "assert result == (200, 199)")
    (working / "check_t01.py").write_text(check_source + "\n")
    check("check_t01", [], "(200, 199)")
    acid.write_text(re.findall(pattern, docs[4], re.S)[0][1] + "\n")
    check("labs.transactions.isolation.acid", [], "after reconnect: [(70,), (130,)]")

for version in (3, 4):
    print(f"T01 v{version} sha256=" + hashlib.sha256(docs[version].encode()).hexdigest())
