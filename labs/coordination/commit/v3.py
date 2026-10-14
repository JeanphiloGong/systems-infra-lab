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
