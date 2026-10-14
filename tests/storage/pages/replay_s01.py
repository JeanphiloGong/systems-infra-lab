"""Replay printed S01 checkpoints and checks outside the working tree."""

import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    tutorials = root / "tutorials/01-storage-engines/01-pages-and-locality"
    for version in range(5):
        guide = (tutorials / f"v{version}/tutorial.md").read_text()
        files = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n```python\n(.*?)\n```", guide, re.S)
        checks = re.findall(r"```bash\nuv run python - <<'PY'\n(.*?)\nPY\n```", guide, re.S)
        assert files and checks, f"v{version}: missing checkpoint/check"
        with TemporaryDirectory(prefix=f"s01-v{version}-") as directory:
            temporary = Path(directory)
            for name, code in files:
                target = temporary / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(code + "\n")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(temporary)
            for check in checks:
                result = subprocess.run(
                    [sys.executable, "-c", check], cwd=temporary, env=env,
                    text=True, capture_output=True, check=True,
                )
                print(result.stdout, end="")
        print(f"v{version}: {len(files)} files replayed")


if __name__ == "__main__":
    main()
