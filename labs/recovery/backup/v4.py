from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import shutil

from common import connect, create_base_backup, recover_at, seed, wait_archive, wait_archived_segments


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory:
        seed(conn)
        base = Path(directory) / "base"
        create_base_backup(base)
        target = conn.execute("SELECT clock_timestamp()::text").fetchone()[0]
        time.sleep(1.1)
        acknowledged_before_target = conn.execute("SELECT count(*) FROM accounts").fetchone()[0]
        start_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        conn.execute("DELETE FROM accounts WHERE id=2")
        conn.execute("INSERT INTO accounts VALUES (3,300)")
        conn.execute("CHECKPOINT")
        end_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        original, segments = wait_archived_segments(conn, start_lsn, end_lsn)
        success_base = Path(directory) / "success-base"
        shutil.copytree(base, success_base)
        success_started = time.monotonic()
        success_ready, success_rows = recover_at(success_base, target, original)
        success_elapsed = time.monotonic() - success_started
        assert success_ready and success_rows == "1:100,2:100"
        archive = Path(directory) / "broken-archive"
        shutil.copytree(original, archive)
        (archive / segments[-1]).unlink()
        failed_started = time.monotonic()
        ready, output = recover_at(base, target, archive, timeout=5)
        failed_elapsed = time.monotonic() - failed_started
        assert not ready and "recovery ended before configured recovery target was reached" in output, output
        return {"missing_archive_detected": True, "recovery_failed": not ready, "error_excerpt": output[-120:],
                "successful_recovery": True, "recovery_elapsed_seconds": success_elapsed,
                "failed_attempt_elapsed_seconds": failed_elapsed,
                "acknowledged_rows_before_target": acknowledged_before_target,
                "recovered_rows": success_rows, "post_target_rows_not_recovered": 1,
                "data_loss_window": "id=3 committed after target and absent from target recovery",
                "required_wal_segments": segments, "archive_continuous": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
