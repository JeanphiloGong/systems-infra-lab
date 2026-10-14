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
