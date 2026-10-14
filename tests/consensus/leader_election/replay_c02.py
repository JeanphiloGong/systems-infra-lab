import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", type=int, choices=range(5))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    versions = range(5) if args.version is None else [args.version]
    for version in versions:
        text = (root / f"tutorials/06-consensus/02-leader-election/v{version}/tutorial.md").read_text()
        files = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
        assert len(files) == 2, "expected complete model and experiment"
        with TemporaryDirectory() as directory:
            base = Path(directory)
            for name, code in files:
                target = base / name
                assert target.resolve().is_relative_to(base)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(code + "\n")
            env = dict(os.environ, PYTHONPATH=str(base))
            result = subprocess.run(
                [sys.executable, "-m", "labs.consensus.leader_election.experiments", str(version)],
                cwd=base, env=env, check=True, capture_output=True, text=True, timeout=30,
            )
            observed = json.loads(result.stdout)
            if version == 0:
                assert len(observed["timeout_self_elected"]) == 3
            elif version == 1:
                assert observed["term1_winner"] != observed["term2_winner"]
            elif version == 2:
                assert observed == {"recovered_term": 7, "recovered_vote": "b", "double_vote_rejected": True}
            elif version == 3:
                assert observed["old_write_rejected"] and observed["value"] == "successor"
            else:
                assert observed["partition"]["old_belief_before_heal"]
                assert not observed["restart"]["old_belief_before_heal"]
                assert all(not result["old_write_allowed"] for result in observed.values())
            print(f"v{version} replay ok: {observed}")


if __name__ == "__main__":
    main()
