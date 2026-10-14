from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    if "SYSTEMS_LAB_DATABASE_URL" not in os.environ:
        print("SKIP: set SYSTEMS_LAB_DATABASE_URL for live PostgreSQL replay")
        return
    root = Path(__file__).resolve().parents[3]
    for version in range(4):
        tutorial = root / f"tutorials/01-storage-engines/07-connections/v{version}/tutorial.md"
        text = tutorial.read_text()
        files = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
        checks = re.findall(r"```bash\n(.*?)\n```", text, re.S)
        assert len(files) == (2 if version == 3 else 1), f"v{version}: unexpected checkpoint count"
        assert checks, f"v{version}: missing check command"
        with TemporaryDirectory() as directory:
            base = Path(directory)
            env = os.environ.copy()
            targets = []
            for name, code in files:
                target = base / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(code + "\n")
                targets.append(target)
            for block in checks:
                for command in block.splitlines():
                    command = command.strip()
                    if not command or command.startswith("export ") or "pytest" in command or command.startswith("docker compose"):
                        continue
                    command = command.replace("uv run python", f"{sys.executable}")
                    if version == 3 and "session_boundary.py" in command:
                        target = base / "session_boundary.py"
                        completed = subprocess.run(command, cwd=base, env=env, shell=True, check=True, capture_output=True, text=True)
                        assert "application_name_after_return': 'f01-v3'" in completed.stdout
                        continue
                    if version == 3 and "proxy.py" in command:
                        if "SYSTEMS_LAB_POOL_URL" not in env:
                            continue
                        completed = subprocess.run(command, cwd=base, env=env, shell=True, check=True, capture_output=True, text=True)
                        assert "session_table_survived': False" in completed.stdout
                        continue
                    completed = subprocess.run(command, cwd=base, env=env, shell=True, check=True, capture_output=True, text=True)
                    if version == 3:
                        assert "application_name_after_return': 'f01-v3'" in completed.stdout
                        assert "transaction_status': 'IDLE'" in completed.stdout
        print(f"v{version} replay ok")


if __name__ == "__main__":
    main()
