# E03 v2: Concurrent appends become explicit conflicts

Two commands may both read version 1. Two file-backed SQLite connections now race with real threads: one expected-version append wins and the other gets Conflict.

## Complete Checkpoint

<!-- checkpoint: labs/dataflows/events/v2.py -->

```python
"""Expected stream versions turn concurrent appends into explicit conflicts."""
from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory


class Conflict(Exception):
    pass


class EventStore:
    def __init__(self, path=":memory:"):
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS events (stream TEXT, version INTEGER, kind TEXT, payload TEXT, PRIMARY KEY(stream,version))")
        self.db.commit()

    def append(self, stream, expected_version, kind, payload):
        self.db.execute("BEGIN IMMEDIATE")
        actual = self.db.execute("SELECT coalesce(max(version),0) FROM events WHERE stream=?", (stream,)).fetchone()[0]
        if actual != expected_version:
            self.db.rollback()
            raise Conflict(f"expected {expected_version}, found {actual}")
        version = actual + 1
        self.db.execute("INSERT INTO events VALUES (?,?,?,?)", (stream, version, kind, json.dumps(payload, sort_keys=True)))
        self.db.commit()
        return version

    def read(self, stream):
        return self.db.execute("SELECT version,kind,payload FROM events WHERE stream=? ORDER BY version", (stream,)).fetchall()


def experiment():
    with TemporaryDirectory() as directory:
        path = str(Path(directory) / "events.sqlite")
        seed = EventStore(path)
        assert seed.append("order-1", 0, "OrderPlaced", {}) == 1
        seed.db.close()

        def append(kind):
            store = EventStore(path)
            try:
                return store.append("order-1", 1, kind, {})
            except Conflict:
                return "conflict"
            finally:
                store.db.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(append, ("OrderPaid", "OrderCancelled")))
        assert sorted(results, key=str).count("conflict") == 1
        store = EventStore(path)
        rows = store.read("order-1")
        assert len(rows) == 2 and rows[1][1] in {"OrderPaid", "OrderCancelled"}
        return {"versions": [row[0] for row in rows], "conflict": "conflict" in results}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## Run And Verify

```bash
uv run python labs/dataflows/events/v2.py
uv run pytest tests/dataflows/events -q
```

The assertions execute the real file-backed writer race (v2) or skipped-version rejection (v3). Replay writes this fence to a fresh directory and runs a new interpreter.

This remains a single-host SQLite teaching model; it is not a distributed transaction coordinator.

