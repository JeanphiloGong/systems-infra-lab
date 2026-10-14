from __future__ import annotations

import json
from pathlib import Path
import tempfile

import psycopg

from common import command, connect, dump, independent_database, seed


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory, independent_database("v0") as target_dsn:
        seed(conn)
        backup = Path(directory) / "accounts.sql"
        dump(backup, "plain")
        command("psql", "--dbname=" + target_dsn, "--file=" + str(backup))
        with connect() as source, psycopg.connect(target_dsn) as restored:
            rows = restored.execute("SELECT * FROM accounts ORDER BY id").fetchall()
            columns = restored.execute("SELECT column_name,is_nullable FROM information_schema.columns WHERE table_name='accounts' ORDER BY ordinal_position").fetchall()
            try:
                restored.execute("INSERT INTO accounts VALUES (1,999)")
            except psycopg.errors.UniqueViolation as error:
                duplicate_sqlstate = error.sqlstate
                restored.rollback()
            try:
                restored.execute("INSERT INTO accounts(id,balance) VALUES (3,NULL)")
            except psycopg.errors.NotNullViolation as error:
                null_sqlstate = error.sqlstate
                restored.rollback()
            assert source.execute("SELECT count(*) FROM accounts").fetchone()[0] == 2
        assert rows == [(1, 100), (2, 100)]
        assert columns == [("id", "NO"), ("balance", "NO")]
        return {"backup": "plain_sql", "rows_restored": len(rows), "round_trip": True,
                "source_preserved": True, "columns": columns,
                "duplicate_sqlstate": duplicate_sqlstate, "null_sqlstate": null_sqlstate}


if __name__ == "__main__":
    print(json.dumps(experiment()))
