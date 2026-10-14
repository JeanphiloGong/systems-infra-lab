# C01 v0: a timeout leaves the outcome unknown

A client sends an operation across a partition. If the response is delayed or dropped, the client cannot infer whether the remote side applied it. Safety requires treating the result as unknown.

<!-- checkpoint: labs/consensus/cap_quorum/v0.py -->

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Message:
    sender: str
    receiver: str
    body: str
    delivered: bool = False


class Partition:
    def __init__(self) -> None:
        self.messages: list[Message] = []
        self.completed: set[str] = set()

    def send(self, sender: str, receiver: str, body: str) -> Message:
        message = Message(sender, receiver, body)
        self.messages.append(message)
        return message

    def deliver(self, message: Message) -> None:
        message.delivered = True
        if message.body.startswith("done:"):
            self.completed.add(message.body.removeprefix("done:"))

    def timeout(self, operation_id: str) -> str:
        return "unknown" if operation_id not in self.completed else "completed"


if __name__ == "__main__":
    network = Partition()
    network.send("A", "B", "apply:op-1")
    print(network.timeout("op-1"))
```

