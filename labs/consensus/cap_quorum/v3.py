from __future__ import annotations

import json
from itertools import combinations


def has_intersection(nodes: set[str], read_size: int, write_size: int) -> bool:
    if not 1 <= read_size <= len(nodes) or not 1 <= write_size <= len(nodes):
        raise ValueError("quorum sizes must fit the node set")
    reads = list(combinations(nodes, read_size))
    writes = list(combinations(nodes, write_size))
    return all(set(read) & set(write) for read in reads for write in writes)


def quorum_read(nodes: set[str], replicas: dict[str, tuple[int, str]], size: int) -> tuple[int, str] | None:
    if size < 1 or size > len(nodes):
        raise ValueError("invalid read quorum")
    observed = sorted((replicas[node] for node in nodes if node in replicas), reverse=True)
    if len(observed) < size:
        return None
    return observed[0]


def concurrent_history() -> dict[str, object]:
    nodes = {"a", "b", "c"}
    replicas = {node: (0, "old") for node in nodes}
    trace = ["invoke write(new)"]
    replicas["a"] = (1, "new")
    acknowledgements = {"a"}
    trace.append("deliver write to a")
    trace.append("invoke read1(a,b)")
    first = quorum_read({"a", "b"}, replicas, 2)
    assert first is not None
    trace.append(f"return read1({first[1]})")
    trace.append("invoke read2(b,c)")
    second = quorum_read({"b", "c"}, replicas, 2)
    assert second is not None
    trace.append(f"return read2({second[1]})")
    replicas["b"] = (1, "new")
    acknowledgements.add("b")
    trace.append("deliver write to b")
    assert len(acknowledgements) >= 2
    trace.append("return write(success)")
    return {
        "intersection": has_intersection(nodes, 2, 2),
        "read_quorums": [["a", "b"], ["b", "c"]],
        "reads": [first, second],
        "write_acks": len(acknowledgements),
        "trace": trace,
    }


if __name__ == "__main__":
    print(json.dumps(concurrent_history(), sort_keys=True))
