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
    parser.add_argument("--version", type=int, choices=range(5))
    args = parser.parse_args()
    if not os.getenv("SYSTEMS_LAB_DATABASE_URL"):
        raise SystemExit("SYSTEMS_LAB_DATABASE_URL is required for live replay")
    root = Path(__file__).resolve().parents[3]
    for version in range(5) if args.version is None else [args.version]:
        text = (root / f"tutorials/04-query/04-derived/v{version}/tutorial.md").read_text()
        files = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
        assert len(files) == (3 if version >= 3 else 2)
        with TemporaryDirectory() as directory:
            for name, code in files:
                target = Path(directory) / name
                assert target.resolve().is_relative_to(Path(directory))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(code + "\n")
            result = subprocess.run([sys.executable, "-m", f"labs.query.derived.v{version}"], cwd=directory,
                env=dict(os.environ, PYTHONPATH=directory), check=True, capture_output=True, text=True, timeout=60)
            result = json.loads(result.stdout)
            result.pop("plans", None)
            print(json.dumps({"version": version, "observed": result}))
        print(f"v{version} live replay ok")


if __name__ == "__main__":
    main()
