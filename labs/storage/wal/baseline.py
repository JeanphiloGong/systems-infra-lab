"""Deliberately unsafe two-step transfer, retained as a failure experiment."""

import argparse
import json
import os
from pathlib import Path


def transfer(path: Path, crash: bool = False) -> None:
    balances = json.loads(path.read_text())
    balances["alice"] -= 10
    path.write_text(json.dumps(balances))
    if crash:
        os._exit(73)
    balances["bob"] += 10
    path.write_text(json.dumps(balances))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--crash", action="store_true")
    args = parser.parse_args()
    transfer(args.path, args.crash)


if __name__ == "__main__":
    main()
