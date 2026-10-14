from __future__ import annotations

import json

from common import connect, reset


def read_event(payload: dict[str, str], consumer: str) -> str:
    if consumer == "old":
        return payload["name"]
    return payload["full_name"] if "full_name" in payload else payload["name"]


def event_matrix() -> dict[str, object]:
    messages = {"old": {"name": "Ada"},
                "transition": {"name": "Ada", "full_name": "Ada"},
                "new": {"full_name": "Ada"}}
    results = {}
    for producer, payload in messages.items():
        for consumer in ("old", "new"):
            try:
                results[f"{producer}->{consumer}"] = read_event(payload, consumer)
            except KeyError:
                results[f"{producer}->{consumer}"] = "rejected"
    assert results == {"old->old": "Ada", "old->new": "Ada",
                       "transition->old": "Ada", "transition->new": "Ada",
                       "new->old": "rejected", "new->new": "Ada"}
    for consumer in ("old", "new"):
        try:
            read_event({}, consumer)
        except KeyError:
            continue
        raise AssertionError("missing event name accepted")
    return results


def experiment() -> dict[str, object]:
    with connect() as conn, connect() as old, connect() as new:
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL)")
        conn.execute("INSERT INTO profiles VALUES (1, 'Ada')")
        conn.execute("ALTER TABLE profiles ADD COLUMN full_name text")
        fallback = new.execute("SELECT COALESCE(full_name,name) FROM profiles WHERE id=1").fetchone()[0]
        old.execute("INSERT INTO profiles(id,name) VALUES (2,'Grace')")
        old_insert_new_read = new.execute("SELECT name FROM profiles WHERE id=2").fetchone()[0]
        new.execute("UPDATE profiles SET name=%s,full_name=%s WHERE id=1", ("Ada Lovelace", "Ada Lovelace"))
        new_write_old_read = old.execute("SELECT name FROM profiles WHERE id=1").fetchone()[0]
        old.execute("UPDATE profiles SET name='Grace' WHERE id=1")
        stale = new.execute("SELECT COALESCE(full_name,name) FROM profiles WHERE id=1").fetchone()[0]
        # During mixed writers, the legacy field is the authoritative read source.
        old_update_new_read = new.execute("SELECT name FROM profiles WHERE id=1").fetchone()[0]
        new.execute("INSERT INTO profiles VALUES (3,'Linus','Linus')")
        new_insert_old_read = old.execute("SELECT name FROM profiles WHERE id=3").fetchone()[0]
        assert (fallback, old_insert_new_read, new_write_old_read, stale, old_update_new_read, new_insert_old_read) == (
            "Ada", "Grace", "Ada Lovelace", "Ada Lovelace", "Grace", "Linus")
        reset(conn)
        return {"fallback": fallback, "old_insert_new_read": old_insert_new_read,
                "new_write_old_read": new_write_old_read, "naive_stale": stale,
                "old_update_new_read": old_update_new_read, "new_insert_old_read": new_insert_old_read,
                "policy": "name authoritative while old writers remain", "additive": True, "dual_write": True,
                "event_matrix": event_matrix()}


if __name__ == "__main__":
    print(json.dumps(experiment()))
