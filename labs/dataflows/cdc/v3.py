from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory

from common import connect, order_change, read_events, snapshot_cut


def worker(database: str, slot: str, failpoint: str) -> None:
    with connect() as source, sqlite3.connect(database) as target:
        events = read_events(source, slot, consume=False)
        assert events
        last = events[-1]
        with target:
            for event in events:
                change = order_change(event)
                if change is None:
                    continue
                identifier, value = change
                if event.operation == "DELETE":
                    target.execute("DELETE FROM projection WHERE id=?", (identifier,))
                else:
                    target.execute("INSERT OR REPLACE INTO projection VALUES (?, ?)", (identifier, value))
            target.execute("INSERT OR IGNORE INTO checkpoint VALUES (?, ?, ?)", (last.source_position, last.key, last.version))
            if failpoint == "before_commit":
                os._exit(17)
        if failpoint == "after_commit":
            os._exit(18)
        # Acknowledge only the committed batch, never later concurrent writes.
        source.execute("SELECT count(*) FROM pg_logical_slot_get_changes(%s, %s::pg_lsn, NULL)", (slot, last.source_position)).fetchone()


def experiment() -> dict[str, object]:
    with TemporaryDirectory() as directory, connect() as source:
        database = str(Path(directory) / "projection.sqlite")
        with sqlite3.connect(database) as target:
            target.execute("CREATE TABLE projection(id INTEGER PRIMARY KEY, value TEXT)")
            target.execute("CREATE TABLE checkpoint(source_position TEXT PRIMARY KEY, event_key TEXT NOT NULL, version INTEGER NOT NULL)")
        source.execute("DROP TABLE IF EXISTS orders")
        source.execute("CREATE TABLE orders(id int PRIMARY KEY, value text)")
        slot = "e01_v3_slot"
        source.execute("SELECT pg_drop_replication_slot(%s) FROM pg_replication_slots WHERE slot_name=%s", (slot, slot))
        source.execute("SELECT * FROM pg_create_logical_replication_slot(%s, 'test_decoding')", (slot,))
        source.execute("INSERT INTO orders VALUES (1,'before-snapshot'),(3,'remove me'),(4,'old incarnation')")
        snapshot, cursor = snapshot_cut(source, slot)
        with sqlite3.connect(database) as target:
            target.executemany("INSERT INTO projection VALUES (?, ?)", snapshot)
        with source.transaction():
            source.execute("UPDATE orders SET value=%s WHERE id=1", ("paid in full; customer's order",))
            source.execute("DELETE FROM orders WHERE id IN (3,4)")
            source.execute("INSERT INTO orders VALUES (4,'new incarnation')")
            source.execute("INSERT INTO orders VALUES (2,'after-snapshot')")
        source_rows = source.execute("SELECT id,value FROM orders ORDER BY id").fetchall()
        expected = read_events(source, slot, consume=False)
        confirmed = source.execute("SELECT confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        try:
            for failpoint, expected_exit in (("before_commit", 17), ("after_commit", 18), ("recover", 0)):
                result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "worker", database, slot, failpoint], capture_output=True, text=True, timeout=15)
                assert result.returncode == expected_exit, result.stderr
                with sqlite3.connect(database) as target:
                    projection = target.execute("SELECT * FROM projection ORDER BY id").fetchall()
                    checkpoints = target.execute("SELECT * FROM checkpoint").fetchall()
                if failpoint == "before_commit":
                    assert projection == snapshot and checkpoints == []
                else:
                    assert projection == source_rows
                    assert checkpoints == [(expected[-1].source_position, expected[-1].key, expected[-1].version)]
                if failpoint != "recover":
                    assert read_events(source, slot, consume=False) == expected
                    assert source.execute("SELECT confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0] == confirmed
            assert read_events(source, slot, consume=False) == []
            advanced = source.execute("SELECT confirmed_flush_lsn > %s::pg_lsn FROM pg_replication_slots WHERE slot_name=%s", (confirmed, slot)).fetchone()[0]
            assert advanced
            return {"projection": projection, "checkpoints": len(checkpoints), "source_position": checkpoints[0][0], "event_key": checkpoints[0][1], "version": checkpoints[0][2], "replay_safe": True, "crash_before_commit_rolled_back": True, "crash_after_commit_replayed": True, "fresh_processes": 3, "source_ack_after_commit": advanced}
        finally:
            source.execute("SELECT pg_drop_replication_slot(%s)", (slot,))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        worker(*sys.argv[2:])
    else:
        print(json.dumps(experiment()))
