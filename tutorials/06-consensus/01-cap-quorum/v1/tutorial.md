# C01 v1: the Two Generals boundary

Adding acknowledgments does not create certainty: the final acknowledgment can itself be lost, and another acknowledgment would have the same problem. This trace is about unreliable communication, not a leader election algorithm.

<!-- checkpoint: labs/consensus/cap_quorum/v1.py -->

```python
from __future__ import annotations


def two_generals_trace() -> list[str]:
    """A final acknowledgment can be lost, so both sides retain uncertainty."""
    return ["A->B:attack", "B->A:ack", "ack lost", "A:uncertain", "B:uncertain"]


def conclude(trace: list[str]) -> str:
    return "coordination incomplete" if "ack lost" in trace else "trace delivered"


if __name__ == "__main__":
    trace = two_generals_trace()
    print(" | ".join(trace))
    print(conclude(trace))
```

