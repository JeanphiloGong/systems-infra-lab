# D03 v2: a crashed coordinator leaves obligations behind

After v1 prepares both resources, disconnecting the coordinator does not roll them back. PostgreSQL keeps them in doubt and keeps their row locks. A timeout tells us that recovery has not completed; it cannot tell a participant to choose abort safely.

## Record the decision before sending it

This checkpoint adds one durable decision journal using SQLite synchronous=FULL on a local temporary disk. Each experiment uses a separate journal for its single distributed transaction. record_decision commits its record before any COMMIT PREPARED message. Rewriting commit as abort is rejected. Recovery reads the same file in the surviving parent process.

This demonstrates coordinator process failure, not loss of its disk or host. The decision journal must remain available and durable for the recovery guarantee. A production coordinator also persists transaction membership and identities; here the supervisor already holds the exact two participant DSNs and GIDs.

## Kill the actual worker and inspect PostgreSQL

The child process prepares both participants, optionally records a decision and optionally commits only the first, then exits abruptly with status 23. The parent queries pg_prepared_xacts and attempts a conflicting UPDATE with lock_timeout=50ms. LockNotAvailable is the observation that prepared work still blocks another writer.

Recovery sends only the durable decision. It can be retried: an already-resolved GID in this isolated transaction is skipped, while the remaining participant gets the same decision. Intermediate balances can be [70, 100] during partial delivery; 2PC atomic commitment is not an instantaneous cross-database snapshot.

## Keep unknown decisions unknown

The missing mode kills the worker before recording any decision. recover returns in_doubt without changing balances or resolving locks. Only after the test supervisor has verified that this worker is permanently stopped and sent no decision does it explicitly record abort and retry recovery. Never infer that authorization from a participant's timeout. Without this knowledge and an intact journal, block and escalate recovery.

Run commit, abort, missing, and commit --partial. The expected final balances are [70, 130] for commit and [100, 100] for abort/missing; --partial first exposes [70, 100] and a lock on only the second resource.

<!-- checkpoint: labs/coordination/commit/pg.py -->

```python
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo


@contextmanager
def resources(prepared: bool = False) -> Iterator[list[str]]:
    """Create two disposable databases on the configured lab server."""
    dsn = os.environ["D03_DATABASE_URL"]
    names: list[str] = []
    with psycopg.connect(dsn, autocommit=True) as admin:
        if prepared and int(admin.execute("SHOW max_prepared_transactions").fetchone()[0]) < 2:
            raise RuntimeError("D03 requires max_prepared_transactions >= 2; restart a disposable server")
        try:
            participants = []
            for _ in range(2):
                name = "d03_" + uuid4().hex
                admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
                names.append(name)
                participant = make_conninfo(dsn, dbname=name)
                participants.append(participant)
                with psycopg.connect(participant, autocommit=True) as conn:
                    conn.execute("CREATE TABLE account (id int PRIMARY KEY, balance int NOT NULL CHECK (balance >= 0))")
                    conn.execute("INSERT INTO account VALUES (1, 100)")
            yield participants
        finally:
            # Resolve only this experiment's transactions before dropping its databases.
            for name in names:
                with psycopg.connect(make_conninfo(dsn, dbname=name), autocommit=True) as conn:
                    for (gid,) in conn.execute("SELECT gid FROM pg_prepared_xacts WHERE database = current_database()").fetchall():
                        conn.execute(sql.SQL("ROLLBACK PREPARED {}").format(sql.Literal(gid)))
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def balances(dsns: list[str]) -> list[int]:
    result = []
    for dsn in dsns:
        with psycopg.connect(dsn) as conn:
            result.append(conn.execute("SELECT balance FROM account WHERE id = 1").fetchone()[0])
    return result
```

<!-- checkpoint: labs/coordination/commit/v2.py -->

```python
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

import psycopg
from psycopg import sql

from pg import balances, resources


def record_decision(path: Path, decision: str) -> None:
    if decision not in {"commit", "abort"}:
        raise ValueError("invalid decision")
    with sqlite3.connect(path) as journal:
        journal.execute("PRAGMA synchronous=FULL")
        journal.execute("CREATE TABLE IF NOT EXISTS decision (id int PRIMARY KEY CHECK(id=1), value text)")
        previous = journal.execute("SELECT value FROM decision WHERE id=1").fetchone()
        if previous is not None and previous[0] != decision:
            raise ValueError("a durable decision cannot change")
        journal.execute("INSERT OR IGNORE INTO decision VALUES (1, ?)", (decision,))


def crash_worker() -> None:
    config = json.loads(os.environ["D03_WORKER"])
    for dsn, gid, delta in zip(config["dsns"], config["gids"], [-30, 30]):
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("BEGIN")
            conn.execute("UPDATE account SET balance=balance+%s WHERE id=1", (delta,))
            conn.execute(sql.SQL("PREPARE TRANSACTION {}").format(sql.Literal(gid)))
    if config["decision"] != "missing":
        record_decision(Path(config["journal"]), config["decision"])
    if config["partial"]:
        with psycopg.connect(config["dsns"][0], autocommit=True) as conn:
            conn.execute(sql.SQL("COMMIT PREPARED {}").format(sql.Literal(config["gids"][0])))
    os._exit(23)


def recover(dsns: list[str], gids: list[str], journal_path: Path) -> str:
    if not journal_path.exists():
        return "in_doubt"
    with sqlite3.connect(journal_path) as journal:
        row = journal.execute("SELECT value FROM decision WHERE id=1").fetchone()
    if row is None:
        return "in_doubt"
    command = "COMMIT" if row[0] == "commit" else "ROLLBACK"
    for dsn, gid in zip(dsns, gids):
        with psycopg.connect(dsn, autocommit=True) as conn:
            pending = conn.execute("SELECT 1 FROM pg_prepared_xacts WHERE gid=%s AND database=current_database()", (gid,)).fetchone()
            if pending:
                conn.execute(sql.SQL(command + " PREPARED {}").format(sql.Literal(gid)))
    return row[0]


def experiment(decision: str = "commit", partial: bool = False) -> dict[str, object]:
    if decision not in {"commit", "abort", "missing"} or (partial and decision != "commit"):
        raise ValueError("partial delivery requires a durable commit")
    with resources(prepared=True) as dsns, TemporaryDirectory() as directory:
        gids = ["d03_" + uuid4().hex for _ in dsns]
        journal = Path(directory) / "decision.sqlite"
        config = {"dsns": dsns, "gids": gids, "journal": str(journal), "decision": decision, "partial": partial}
        worker = subprocess.run([sys.executable, __file__, "worker"], env={**os.environ, "D03_WORKER": json.dumps(config)}, capture_output=True, text=True, timeout=20)
        assert worker.returncode == 23, worker.stderr
        before = balances(dsns)
        locks = []
        pending_count = 0
        for dsn in dsns:
            with psycopg.connect(dsn, autocommit=True) as conn:
                pending_count += conn.execute("SELECT count(*) FROM pg_prepared_xacts WHERE database=current_database()").fetchone()[0]
                conn.execute("SET lock_timeout='50ms'")
                try:
                    conn.execute("UPDATE account SET balance=balance WHERE id=1")
                    locks.append(False)
                except psycopg.errors.LockNotAvailable:
                    locks.append(True)
        outcome = recover(dsns, gids, journal)
        assert locks == ([False, True] if partial else [True, True])
        assert pending_count == (1 if partial else 2)
        if decision == "missing":
            assert outcome == "in_doubt" and balances(dsns) == [100, 100]
            # Operator has verified this coordinator died before sending ANY decision.
            record_decision(journal, "abort")
            outcome = recover(dsns, gids, journal)
        assert recover(dsns, gids, journal) == outcome
        after = balances(dsns)
        assert after == ([70, 130] if decision == "commit" else [100, 100])
        return {"decision": decision, "partial": partial, "before": before, "pending": pending_count, "locked": locks, "after": after, "resolved": outcome}


if __name__ == "__main__":
    if sys.argv[1:] == ["worker"]:
        crash_worker()
    else:
        mode = sys.argv[1] if len(sys.argv) > 1 else "commit"
        print(json.dumps(experiment(mode, partial="--partial" in sys.argv)))
```

## Checkpoint

Run from the repository root:

```bash
uv run python labs/coordination/commit/v2.py
uv run python labs/coordination/commit/v2.py abort
uv run python labs/coordination/commit/v2.py missing
uv run python labs/coordination/commit/v2.py commit --partial
```

The replay suite extracts only these complete fences into a fresh temporary directory and verifies the reported behavior. Run `uv run python -m pytest tests/coordination/commit -q` with the disposable database configured.

Before moving on, verify repeated recovery returns the same outcome. Do not delete an unresolved production journal or roll back a prepared participant merely because its peer is slow.

