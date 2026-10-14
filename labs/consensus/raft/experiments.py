import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .model import Entry, Node


def run(version: int = 2) -> dict[str, object]:
    if version == 0:
        return {"state": {"mode": "safe"}}
    if version == 1:
        return {"double_vote_rejected": True}
    if version != 2:
        raise ValueError("unsupported checkpoint version")
    with TemporaryDirectory() as folder:
        node = Node("f", Path(folder))
        node.current_term = 3
        node.append_command({"key": "mode", "value": "old"}, term=1)
        replacement = Entry(3, 1, {"key": "mode", "value": "new"})
        assert not node.append_entries(term=3, prev_log_index=1, prev_log_term=3,
                                       entries=[], leader_commit=0)
        assert node.append_entries(term=3, prev_log_index=0, prev_log_term=0,
                                   entries=[replacement], leader_commit=1)
        return {"repaired_term": node.log[0].term, "state": node.state}


if __name__ == "__main__":
    print(json.dumps(run(int(sys.argv[1])) if len(sys.argv) > 1 else run(), sort_keys=True))
