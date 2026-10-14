"""Independently replay T01 v0's printed baseline, patch, and checkpoint."""

import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
document = ROOT / "tutorials/02-transactions-isolation/01-isolation/v0/tutorial.md"
text = document.read_text()
blocks = re.findall(r"```(\w+)\n(.*?)\n```", text, re.S)
python = [body for language, body in blocks if language == "python"]
schema = next(body for language, body in blocks if language == "sql")

with tempfile.TemporaryDirectory(prefix="t01-review-") as directory:
    working = Path(directory)
    target = working / "labs/transactions/isolation/transfer.py"
    target.parent.mkdir(parents=True)
    target.write_text(python[-1] + "\n")
    target.with_name("schema.sql").write_text(schema + "\n")
    baseline = working / "baseline.py"
    baseline.write_text(python[0] + "\n")
    broken = working / "broken.py"
    broken.write_text(python[0].replace(
        '        conn.execute("UPDATE accounts SET balance=balance+%s WHERE id=2", (30,))',
        python[1]) + "\n")

    def check(arguments: list[str], expected: str, fails: bool = False, env=None) -> None:
        result = subprocess.run([str(ROOT / ".venv/bin/python"), *arguments], cwd=working,
                                capture_output=True, text=True, env=env)
        assert (result.returncode != 0) == fails, result.stdout + result.stderr
        assert expected in result.stdout + result.stderr, result.stdout + result.stderr
        print(arguments, "PASS", result.stdout.strip())

    check([str(baseline)], "[(70,), (130,)]")
    check([str(broken)], "[(70,), (100,)]", fails=True)
    check(["-m", "labs.transactions.isolation.transfer", "--amount", "30"], "[(1, 70), (2, 130)]")
    check(["-m", "labs.transactions.isolation.transfer", "--amount", "30", "--fail-after-debit"],
          "[(1, 100), (2, 100)]", fails=True)
    check(["-m", "labs.transactions.isolation.transfer", "--amount", "0"],
          "[(1, 100), (2, 100)]", fails=True)
    env = dict(os.environ, SYSTEMS_LAB_DATABASE_URL="postgresql://systems_lab:unused@127.0.0.1:1/systems_lab")
    check(["-m", "labs.transactions.isolation.transfer"], "OperationalError", fails=True, env=env)

print("tutorial_sha256=" + hashlib.sha256(document.read_bytes()).hexdigest())
print("checkpoint_sha256=" + hashlib.sha256(python[-1].encode()).hexdigest())
