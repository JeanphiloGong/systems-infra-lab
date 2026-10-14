from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from common import connect, reset


def backfill(conn: object, batch_size: int = 2, failpoint: str | None = None) -> tuple[int, int | None]:
    processed = 0
    cursor = conn.execute("SELECT last_id FROM schema_backfill_checkpoint WHERE job=%s", ("profiles_full_name",)).fetchone()[0]
    while True:
        if cursor is None:
            rows = conn.execute("SELECT id,name FROM profiles WHERE full_name IS NULL ORDER BY id LIMIT %s", (batch_size,)).fetchall()
        else:
            rows = conn.execute("SELECT id,name FROM profiles WHERE full_name IS NULL AND id > %s ORDER BY id LIMIT %s", (cursor, batch_size)).fetchall()
        if not rows:
            return processed, cursor
        with conn.transaction():
            for identifier, name in rows:
                conn.execute("UPDATE profiles SET full_name=%s WHERE id=%s AND full_name IS NULL", (name, identifier))
            if failpoint == "before_commit":
                os._exit(19)
            conn.execute("UPDATE schema_backfill_checkpoint SET last_id=%s WHERE job=%s", (rows[-1][0], "profiles_full_name"))
        processed += len(rows)
        cursor = rows[-1][0]
        if failpoint == "after_commit":
            os._exit(17)


def experiment() -> dict[str, object]:
    with connect() as conn:
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL, full_name text)")
        conn.execute("CREATE TABLE schema_backfill_checkpoint(job text PRIMARY KEY, last_id integer)")
        conn.execute("INSERT INTO schema_backfill_checkpoint VALUES ('profiles_full_name', NULL)")
        with conn.cursor() as cursor:
            cursor.executemany("INSERT INTO profiles(id,name) VALUES (%s,%s)", [(1, "Ada"), (2, "Grace"), (3, "Linus"), (4, "Margaret"), (5, "Ken")])
        conn.execute("UPDATE profiles SET full_name='Protected by new client' WHERE id=5")
        # The migration starts only after old writers are drained. New writers dual-write.
        conn.execute("UPDATE profiles SET name=full_name WHERE id=5")
        conn.execute("UPDATE profiles SET full_name='stale old value' WHERE id=1")
        # Repair mixed-writer divergence before advancing the NULL-only backfill cursor.
        conn.execute("UPDATE profiles SET full_name=NULL WHERE full_name IS DISTINCT FROM name AND full_name IS NOT NULL")
        script = str(Path(__file__).resolve())
        first = subprocess.run([sys.executable, script, "worker", "after_commit"], env=os.environ, capture_output=True, text=True, timeout=15)
        assert first.returncode == 17
        checkpoint = conn.execute("SELECT last_id FROM schema_backfill_checkpoint WHERE job=%s", ("profiles_full_name",)).fetchone()[0]
        first_batch = conn.execute("SELECT count(*) FROM profiles WHERE id < 5 AND full_name IS NOT NULL").fetchone()[0]
        assert checkpoint == first_batch == 2
        failed = subprocess.run([sys.executable, script, "worker", "before_commit"], env=os.environ, capture_output=True, text=True, timeout=15)
        assert failed.returncode == 19
        assert conn.execute("SELECT last_id FROM schema_backfill_checkpoint WHERE job=%s", ("profiles_full_name",)).fetchone()[0] == checkpoint
        assert conn.execute("SELECT count(*) FROM profiles WHERE id IN (3,4) AND full_name IS NULL").fetchone()[0] == 2
        resumed = subprocess.run([sys.executable, script, "worker", "normal"], env=os.environ, capture_output=True, text=True, timeout=15)
        assert resumed.returncode == 0, resumed.stderr
        repeated = subprocess.run([sys.executable, script, "worker", "normal"], env=os.environ, capture_output=True, text=True, timeout=15)
        assert repeated.returncode == 0, repeated.stderr
        resume_batch, resume_cursor = json.loads(resumed.stdout)
        repeat_batch, repeat_cursor = json.loads(repeated.stdout)
        assert (resume_batch, resume_cursor, repeat_batch, repeat_cursor) == (2, 4, 0, 4)
        remaining = conn.execute("SELECT count(*) FROM profiles WHERE full_name IS NULL").fetchone()[0]
        protected = conn.execute("SELECT full_name FROM profiles WHERE id=5").fetchone()[0]
        assert remaining == 0 and protected == "Protected by new client"
        reset(conn)
        return {"first_batch": first_batch, "checkpoint": checkpoint, "resume_batch": resume_batch, "repeat_batch": repeat_batch, "remaining": remaining, "protected": protected, "process_failure_recovered": True, "uncommitted_batch_rolled_back": True, "fresh_repeat_zero_work": repeat_batch == 0, "resumable": True}


def worker(failpoint: str) -> None:
    with connect() as conn:
        print(json.dumps(backfill(conn, failpoint=None if failpoint == "normal" else failpoint)))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        worker(sys.argv[2])
    else:
        print(json.dumps(experiment()))
