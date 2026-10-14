from __future__ import annotations

import json
from pathlib import Path
import tempfile

from common import command, connect, create_base_backup, dump, seed, wait_archived_segments


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory:
        seed(conn)
        backup = Path(directory) / "accounts.dump"
        dump(backup)
        raw = backup.read_bytes()
        backup.write_bytes(raw[: max(1, len(raw) // 2)])
        conn.execute("DROP TABLE accounts")
        failed = False
        try:
            command("pg_restore", "--dbname=" + conn.info.dsn, str(backup))
        except Exception:
            failed = True
        assert failed
        seed(conn)
        start_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        conn.execute("INSERT INTO accounts VALUES (3,300)")
        conn.execute("CHECKPOINT")
        end_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        base = Path(directory) / "base"
        create_base_backup(base)
        conn.execute("SELECT pg_switch_wal()")
        archive, segments = wait_archived_segments(conn, start_lsn, end_lsn)
        assert segments and all((archive / segment).stat().st_size == 16777216 for segment in segments)
        return {"corruption_detected": True, "partial_restore_accepted": False,
                "physical_backup": True, "base_backup_complete": (base / "PG_VERSION").exists(),
                "wal_start_lsn": start_lsn, "wal_end_lsn": end_lsn,
                "required_wal_segments": segments, "archive_continuous": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
