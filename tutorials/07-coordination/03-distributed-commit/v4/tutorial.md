# D03 v4: violate the timing and partition assumptions

A pre-commit phase alone cannot guarantee atomic commitment and nonblocking progress under arbitrary asynchronous partitions. Reuse v3's state machine and deliver prepare to both participants, then deliver precommit only to the first. The coordinator disappears before the second sees that message, and the participants cannot exchange termination information.

## Turn an unsafe timeout shortcut into a counterexample

A tempting shortcut is: READY aborts on timeout; PRECOMMIT commits on timeout. The function is intentionally named unsafe_timeout because this is not a complete 3PC termination protocol. Under the partition the first commits and the second aborts. That is an explicit violation of our atomic outcome invariant.

Before the timeout states are [precommit, ready]; afterwards they are [committed, aborted]. Nothing about a longer timeout changes the impossibility of distinguishing permanent failure from unbounded delay. Safe operation in this unknown-delay model must keep the uncertain outcome unresolved rather than use this shortcut.

Classical nonblocking 3PC arguments rely on restricted synchronous failure models, including timing bounds and conditions allowing a termination protocol to communicate. This counterexample shows why removing those conditions invalidates a local timeout rule; it is not a claim that v3 was a full implementation of those protocols.

## Keep atomic commit distinct from consensus

2PC coordinates whether all transaction resources commit after voting; it can block. Consensus agrees on a value among replicas under its own fault model. Replicating a coordinator decision using a mature consensus service can improve availability, but does not let an unavailable participant release an in-doubt lock by guessing. This tutorial implements neither Raft nor a fault-tolerant transaction manager.

<!-- checkpoint: labs/coordination/commit/v3.py -->

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json


class State(Enum):
    INIT = "init"
    READY = "ready"
    PRECOMMIT = "precommit"
    COMMITTED = "committed"
    ABORTED = "aborted"


@dataclass
class Participant:
    state: State = State.INIT

    def receive(self, message: str) -> str:
        transitions = {
            (State.INIT, "prepare"): (State.READY, "yes"),
            (State.READY, "precommit"): (State.PRECOMMIT, "ack"),
            (State.PRECOMMIT, "commit"): (State.COMMITTED, "done"),
            (State.READY, "abort"): (State.ABORTED, "done"),
        }
        if (self.state, message) not in transitions:
            raise ValueError("illegal phase transition")
        self.state, reply = transitions[(self.state, message)]
        return reply


def experiment() -> dict[str, object]:
    participants = [Participant(), Participant()]
    history = []
    messages = 0
    for phase in ["prepare", "precommit", "commit"]:
        for participant in participants:
            participant.receive(phase)
            messages += 2  # A delivered command plus its reply.
        history.append([participant.state.value for participant in participants])
    assert history == [["ready", "ready"], ["precommit", "precommit"], ["committed", "committed"]]
    return {"history": history, "messages_3pc": messages, "messages_2pc": 8}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

<!-- checkpoint: labs/coordination/commit/v4.py -->

```python
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
```

## Checkpoint

Run from the repository root:

```bash
uv run python labs/coordination/commit/v4.py
```

The replay suite extracts only these complete fences into a fresh temporary directory and verifies the reported behavior. Run `uv run python -m pytest tests/coordination/commit -q` with the disposable database configured.

Before moving on, distinguish the intentionally unsafe counterexample from a usable implementation. Neither the extra phase nor quorum arithmetic alone supplies distributed transaction recovery.

