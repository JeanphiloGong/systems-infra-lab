# Q01 build evidence

Implemented `labs/query/modeling/model.py` with normalized customer/product/order entities and an explicit denormalized read model. Added v0-v3 tutorials under `tutorials/04-query/01-modeling/`, focused tests, and isolated replay.

Verification:

```text
uv run pytest tests/query/modeling -q
4 passed

uv run python tests/query/modeling/replay_q01.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

The examples measure logical joins and maintenance writes, and explicitly show stale read-model state. They do not claim database optimizer or hardware performance.

v3 now inserts a distinct later order for the new price and asserts the original purchase price remains unchanged.
