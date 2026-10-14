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
        text = (root / f"tutorials/04-query/02-indexes/v{version}/tutorial.md").read_text()
        matches = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
        assert len(matches) == 1
        with TemporaryDirectory() as directory:
            name, code = matches[0]
            checkpoint = root / f"labs/query/indexes/checkpoints/v{version}.py"
            assert checkpoint.exists(), checkpoint
            assert code.rstrip() == checkpoint.read_text().rstrip(), checkpoint
            target = Path(directory) / name
            target.write_text(checkpoint.read_text() + "\n")
            result = subprocess.run([sys.executable, str(target), str(version)], cwd=directory,
                env=dict(os.environ, PYTHONPATH=directory), check=True, capture_output=True, text=True, timeout=60)
            result = json.loads(result.stdout)
            print(json.dumps({"version": version, "server": result["server"], "metrics": result["metrics"]}))
        print(f"v{version} live replay ok")


if __name__ == "__main__":
    main()
