from __future__ import annotations

import json

import psycopg

from common import connect, reset


def contract(conn: psycopg.Connection) -> None:
    with conn.transaction():
        conn.execute("LOCK TABLE profiles, migration_clients IN ACCESS EXCLUSIVE MODE")
        if conn.execute("SELECT count(*) FROM migration_clients WHERE protocol='old' AND active").fetchone()[0]:
            raise RuntimeError("old clients remain")
        if conn.execute("SELECT count(*) FROM profiles WHERE full_name IS NULL").fetchone()[0]:
            raise RuntimeError("backfill incomplete")
        conn.execute("ALTER TABLE profiles ALTER COLUMN full_name SET NOT NULL")
        conn.execute("ALTER TABLE profiles DROP COLUMN name")
        conn.execute("DROP TABLE schema_backfill_checkpoint, migration_clients")


def read_event(payload: dict[str, str]) -> str:
    value = payload["full_name"]
    if not isinstance(value, str) or not value:
        raise ValueError("full_name must be a nonempty string")
    return value


def experiment() -> dict[str, object]:
    with connect() as conn:
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL, full_name text)")
        conn.execute("CREATE TABLE migration_clients(protocol text, active boolean)")
        conn.execute("INSERT INTO migration_clients VALUES ('old',true)")
        conn.execute("CREATE TABLE schema_backfill_checkpoint(last_id integer)")
        with conn.cursor() as cursor:
            cursor.executemany("INSERT INTO profiles(id,name,full_name) VALUES (%s,%s,%s)", [(1, "Ada", "Ada"), (2, "Grace", "Grace")])
        try:
            contract(conn)
        except RuntimeError as error:
            assert str(error) == "old clients remain"
        else:
            raise AssertionError("retirement gate bypassed")
        conn.execute("UPDATE migration_clients SET active=false")
        conn.execute("UPDATE profiles SET full_name=NULL WHERE id=2")
        try:
            contract(conn)
        except RuntimeError as error:
            assert str(error) == "backfill incomplete"
        else:
            raise AssertionError("backfill gate bypassed")
        conn.execute("UPDATE profiles SET full_name=name WHERE id=2")
        contract(conn)
        rejected = []
        for statement in ("INSERT INTO profiles(id,full_name) VALUES (3,NULL)",
                          "INSERT INTO profiles(id) VALUES (3)",
                          "UPDATE profiles SET full_name=NULL WHERE id=1"):
            try:
                conn.execute(statement)
            except psycopg.errors.NotNullViolation as error:
                rejected.append(error.sqlstate)
            else:
                raise AssertionError("required field violation accepted")
        conn.execute("INSERT INTO profiles VALUES (3,'Linus')")
        new_read = conn.execute("SELECT full_name FROM profiles ORDER BY id").fetchall()
        try:
            conn.execute("SELECT name FROM profiles")
        except psycopg.errors.UndefinedColumn:
            old_rejected = True
        else:
            old_rejected = False
        assert new_read == [("Ada",), ("Grace",), ("Linus",)] and old_rejected
        columns = conn.execute("SELECT column_name,is_nullable FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='profiles' ORDER BY ordinal_position").fetchall()
        assert columns == [("id", "NO"), ("full_name", "NO")]
        artifacts = conn.execute("SELECT to_regclass('schema_backfill_checkpoint'),to_regclass('migration_clients')").fetchone()
        assert artifacts == (None, None)
        events = []
        for payload in ({"name": "Ada"}, {}, {"full_name": None}, {"full_name": ""}):
            try:
                read_event(payload)
            except (KeyError, ValueError):
                events.append("rejected")
            else:
                raise AssertionError("final consumer accepted invalid event")
        assert read_event({"full_name": "Linus"}) == "Linus"
        reset(conn)
        return {"new_rows": len(new_read), "not_null": columns[1][1] == "NO",
                "old_client_rejected": old_rejected, "cleanup_complete": artifacts == (None, None),
                "write_rejections": rejected, "retirement_gate": "blocked until retired",
                "event_rejections": events, "final_event": "Linus"}


if __name__ == "__main__":
    print(json.dumps(experiment()))
