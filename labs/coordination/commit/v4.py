from __future__ import annotations

import json

from v3 import Participant, State


def unsafe_timeout(participant: Participant) -> None:
    """An intentionally unsafe rule under partitions, NOT a 3PC protocol."""
    if participant.state is State.PRECOMMIT:
        participant.state = State.COMMITTED
    elif participant.state is State.READY:
        participant.state = State.ABORTED
    else:
        raise ValueError("timeout only modeled in uncertain phases")


def experiment() -> dict[str, object]:
    first, second = Participant(), Participant()
    first.receive("prepare")
    second.receive("prepare")
    first.receive("precommit")
    # Coordinator disappears, and the participants cannot contact each other.
    before = [first.state.value, second.state.value]
    unsafe_timeout(first)
    unsafe_timeout(second)
    after = [first.state.value, second.state.value]
    assert before == ["precommit", "ready"]
    assert after == ["committed", "aborted"]
    return {"before": before, "after": after, "atomic": False, "safe_action_under_unknown_delay": "block"}


if __name__ == "__main__":
    print(json.dumps(experiment()))
