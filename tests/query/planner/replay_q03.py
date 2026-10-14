import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", type=int, choices=range(4))
    args = parser.parse_args()
    if not os.getenv("SYSTEMS_LAB_DATABASE_URL"):
        raise SystemExit("SYSTEMS_LAB_DATABASE_URL is required for live replay")
    root = Path(__file__).resolve().parents[3]
    for version in range(4) if args.version is None else [args.version]:
        text = (root / f"tutorials/04-query/03-planner/v{version}/tutorial.md").read_text()
        files = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
        assert len(files) == 1
        with TemporaryDirectory() as directory:
            name, code = files[0]
            target = Path(directory) / name
            target.write_text(code + "\n")
            result = subprocess.run([sys.executable, str(target)], cwd=directory,
                env=dict(os.environ, PYTHONPATH=directory), check=True, capture_output=True, text=True, timeout=90)
            result = json.loads(result.stdout)
            print(json.dumps({"version": version, "server": result["server"], "metrics": result["metrics"]}))
        print(f"v{version} live replay ok")


if __name__ == "__main__":
    main()
