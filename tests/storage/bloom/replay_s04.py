import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    for version in range(4):
        text = (root / f"tutorials/01-storage-engines/04-bloom-filter/v{version}/tutorial.md").read_text()
        files = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n```python\n(.*?)\n```", text, re.S)
        checks = re.findall(r"```bash\nuv run python - <<'PY'\n(.*?)\nPY\n```", text, re.S)
        assert files and checks, f"missing v{version} checkpoint"
        with TemporaryDirectory() as directory:
            base = Path(directory)
            for name, code in files:
                target = base / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(code + "\n")
            env = os.environ.copy(); env["PYTHONPATH"] = str(base)
            for check in checks:
                subprocess.run([sys.executable, "-c", check], cwd=base, env=env, check=True)
        print(f"v{version} replay ok")


if __name__ == "__main__":
    main()
