from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    for version in range(5):
        text = (root / f"tutorials/02-traffic/02-admission/v{version}/tutorial.md").read_text()
        files = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
        assert len(files) == 1, f"v{version}: expected one source checkpoint"
        with TemporaryDirectory() as directory:
            target = Path(directory) / files[0][0]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(files[0][1] + "\n")
            subprocess.run([sys.executable, str(target)], cwd=directory, check=True, capture_output=True, text=True)
        print(f"v{version} replay ok")


if __name__ == "__main__":
    main()
