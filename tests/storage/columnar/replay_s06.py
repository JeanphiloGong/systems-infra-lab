import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    for version in range(5):
        text = (root / f"tutorials/01-storage-engines/06-columnar-storage/v{version}/tutorial.md").read_text()
        checks = re.findall(r"```bash\nuv run python - <<'PY'\n(.*?)\nPY\n```", text, re.S)
        files = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n```python\n(.*?)\n```", text, re.S)
        assert files and checks, f"missing v{version} checkpoint/check"
        with TemporaryDirectory() as directory:
            base = Path(directory)
            for name, code in files:
                target = base / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(code + "\n")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(base)
            for check in checks:
                subprocess.run([sys.executable, "-c", check], cwd=directory, env=env, check=True)
        print(f"v{version} replay ok")


if __name__ == "__main__":
    main()
