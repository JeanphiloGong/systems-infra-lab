# D03 v3: add a pre-commit phase

v2 shows 2PC's uncertainty: a prepared participant cannot safely decide alone when its coordinator disappears. Three-phase commit introduces a pre-commit state between a yes vote and a final commit, so termination reasoning can distinguish those stages under its timing and failure assumptions.

This checkpoint is a deterministic state-machine model, not PostgreSQL 3PC. It models two participants, explicit legal messages and delivered replies. It omits recovery elections and does not claim to implement a complete nonblocking termination protocol.

## Make the extra round visible

prepare moves INIT to READY and returns yes. After all yes replies, precommit moves READY to PRECOMMIT and returns ack. Only after all acknowledgments does commit move participants to COMMITTED. A READY participant may abort; an arbitrary phase jump is rejected.

Count delivered messages in a failure-free run, including command and reply for each participant. Two participants across three rounds cost 12 messages versus 8 for a comparable two-round 2PC exchange. Counts exclude logging, retries and elections, and depend on including final acknowledgments.

The observed history must be ready/ready, precommit/precommit, committed/committed. The extra round provides information; it does not eliminate the need for assumptions about bounded communication and admissible failures. v4 deliberately violates those assumptions.

将下面的完整代码保存为 `labs/coordination/commit/v3.py`；文件已存在时，以本版内容替换该文件。

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

## Checkpoint

Run from the repository root:

```bash
uv run python labs/coordination/commit/v3.py
```

The optional reference-branch replay suite extracts only these complete fences into a fresh temporary directory and verifies the reported behavior. Optional: use [参考分支检查](../../../../docs/reference-checks.md) with the disposable database configured.

Before moving on, try commit directly from READY: it must raise ValueError. v4 explores what happens when participants cannot exchange the information needed to terminate.

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/coordination/commit -q
```

</details>
