# E03 v0：当前状态没有来路

仪表盘只保留 order_id -> paid。这个值能回答当前状态，却不能解释何时下单、何时付款，也不能重建审计轨迹。先把限制写成可运行基线。

## Complete Checkpoint

<!-- checkpoint: labs/dataflows/events/v0.py -->

```python
"""A current-state row cannot explain how an order changed."""
import json


def current_state():
    return {"order-1": "paid"}


def experiment():
    state = current_state()
    assert state["order-1"] == "paid"
    return {"state": state, "history_available": False, "explanation": "current row stores result only"}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## Run And Verify

```bash
uv run python labs/dataflows/events/v0.py
uv run pytest tests/dataflows/events -q
```

The assertions check this version's behavior. The replay test writes this fence into a fresh temporary directory and runs a new interpreter without hidden repository imports.

运行 current_state() 并断言没有历史；下一版把变化写成事实事件。

This is a single SQLite teaching model. It does not provide cross-service transactions, global event ordering, distributed projection coordination or CDC. Event Sourcing treats domain events as facts; it is not change capture from an existing table.

