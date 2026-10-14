from __future__ import annotations

import json
import psycopg

from common import connect, reset


def experiment() -> dict[str, object]:
    with connect() as conn:
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL)")
        conn.execute("INSERT INTO profiles VALUES (1, 'Ada')")
        old_client = conn.execute("SELECT name FROM profiles WHERE id=1").fetchone()[0]
        conn.execute("ALTER TABLE profiles RENAME COLUMN name TO full_name")
        try:
            conn.execute("SELECT name FROM profiles WHERE id=1")
        except psycopg.errors.UndefinedColumn:
            broken = True
        else:
            broken = False
        assert old_client == "Ada" and broken
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL)")
        conn.execute("ALTER TABLE profiles ADD COLUMN full_name text NOT NULL")
        try:
            conn.execute("INSERT INTO profiles(id,name) VALUES (1,'Ada')")
        except psycopg.errors.NotNullViolation as error:
            old_write_error = error.sqlstate
        else:
            raise AssertionError("old writer unexpectedly satisfied new required field")
        conn.execute("ALTER TABLE profiles DROP COLUMN full_name")
        conn.execute("INSERT INTO profiles VALUES (1,'Ada')")
        try:
            conn.execute("ALTER TABLE profiles ADD COLUMN full_name text NOT NULL")
        except psycopg.errors.NotNullViolation as error:
            populated_ddl_error = error.sqlstate
        else:
            raise AssertionError("existing NULL values unexpectedly accepted")
        reset(conn)
        return {"old_client_value": old_client, "rename_breaks_old_client": broken,
                "old_write_sqlstate": old_write_error, "populated_ddl_sqlstate": populated_ddl_error}


if __name__ == "__main__":
    print(json.dumps(experiment()))
