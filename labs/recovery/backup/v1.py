from __future__ import annotations

import json
from pathlib import Path
import tempfile

import psycopg

from common import command, connect, dump, independent_database, seed


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory, independent_database("v1") as target_dsn:
        seed(conn)
        backup = Path(directory) / "accounts.dump"
        dump(backup)
        conn.execute("INSERT INTO accounts VALUES (3,50)")
        command("pg_restore", "--dbname=" + target_dsn, str(backup))
        with connect() as source, psycopg.connect(target_dsn) as restored:
            rows = restored.execute("SELECT * FROM accounts ORDER BY id").fetchall()
            source_rows = source.execute("SELECT * FROM accounts ORDER BY id").fetchall()
        assert rows == [(1, 100), (2, 100)]
        assert source_rows == [(1, 100), (2, 100), (3, 50)]
        return {"backup": "custom_format", "rows_at_backup": len(rows), "post_backup_row_excluded": True, "source_preserved": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
