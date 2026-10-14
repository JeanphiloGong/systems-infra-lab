import argparse
import json
import os
from pathlib import Path

from labs.storage.wal.store import Store


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("action", choices=("write", "recover"))
    parser.add_argument("--crash-at", default="")
    args = parser.parse_args()

    def event(name: str) -> None:
        if name == args.crash_at:
            os._exit(73)

    store = Store(args.directory, event=event)
    if args.action == "recover":
        print(json.dumps(store.recover(), sort_keys=True))
        return
    store.commit("t1", {"alice": 90, "bob": 110})
    print("ACK", flush=True)
    event("after_ack")


if __name__ == "__main__":
    main()
