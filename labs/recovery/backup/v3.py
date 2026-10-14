from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time

from common import connect, create_base_backup, recover_at, seed, wait_archive, wait_archived_segments


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory:
        seed(conn)
        start_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        base = Path(directory) / "base"
        create_base_backup(base)
        target = conn.execute("SELECT clock_timestamp()::text").fetchone()[0]
        time.sleep(1.1)
        conn.execute("DELETE FROM accounts WHERE id=2")
        conn.execute("INSERT INTO accounts VALUES (3,300)")
        conn.execute("CHECKPOINT")
        end_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        archive, segments = wait_archived_segments(conn, start_lsn, end_lsn)
        ready, rows = recover_at(base, target, archive)
        assert ready and rows == "1:100,2:100", rows
        current = conn.execute("SELECT string_agg(id::text || ':' || balance::text, ',' ORDER BY id) FROM accounts").fetchone()[0]
        assert current == "1:100,3:300"
        return {"physical_backup": True, "base_backup_complete": True, "target_rows": rows, "later_rows_absent": True, "deleted_row_restored": True, "current_rows": current,
                "wal_start_lsn": start_lsn, "wal_end_lsn": end_lsn, "required_wal_segments": segments,
                "archive_continuous": all((archive / segment).stat().st_size == 16777216 for segment in segments)}


if __name__ == "__main__":
    print(json.dumps(experiment()))
