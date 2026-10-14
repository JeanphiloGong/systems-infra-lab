from __future__ import annotations

import json
import psycopg

from common import connect, scalar, wait_for
from v1 import setup


def experiment() -> dict[str, object]:
    setup()
    with connect("primary") as primary, connect("subscriber") as subscriber, connect("standby") as standby:
        primary.execute("ALTER TABLE orders ADD COLUMN note text")
        target = str(scalar(primary, "SELECT pg_current_wal_lsn()"))
        wait_for(lambda: standby.execute("SELECT pg_last_wal_replay_lsn() >= %s::pg_lsn", (target,)).fetchone()[0], "physical DDL")
        columns = "SELECT column_name FROM information_schema.columns WHERE table_name='orders' AND column_name='note'"
        assert primary.execute(columns).fetchall() == [("note",)]
        assert standby.execute(columns).fetchall() == [("note",)]
        assert subscriber.execute(columns).fetchall() == []
        subscriber.execute("ALTER TABLE orders ADD COLUMN note text")
        primary.execute("INSERT INTO orders(value,note) VALUES ('next','manual schema aligned')")
        wait_for(lambda: scalar(subscriber, "SELECT note FROM orders WHERE id=2") == "manual schema aligned", "aligned DDL data")
        try:
            subscriber.execute("INSERT INTO orders(value) VALUES ('local-write-collision')")
        except psycopg.errors.UniqueViolation:
            sequence_collision = True
        else:
            raise AssertionError("subscriber sequence unexpectedly followed publisher")
        primary_sequence = scalar(primary, "SELECT last_value FROM orders_id_seq")
        subscriber_sequence = scalar(subscriber, "SELECT last_value FROM orders_id_seq")
        assert primary_sequence == 2 and subscriber_sequence == 1
        primary.execute("ALTER TABLE orders REPLICA IDENTITY NOTHING")
        try:
            primary.execute("UPDATE orders SET value='must fail' WHERE id=2")
        except psycopg.errors.ObjectNotInPrerequisiteState:
            identity_rejected = True
        else:
            raise AssertionError("UPDATE accepted without replica identity")
        primary.execute("ALTER TABLE orders REPLICA IDENTITY FULL")
        primary.execute("UPDATE orders SET value='full identity' WHERE id=2")
        wait_for(lambda: scalar(subscriber, "SELECT value FROM orders WHERE id=2") == "full identity", "FULL identity update")
        primary.execute("DELETE FROM orders WHERE id=1")
        wait_for(lambda: scalar(subscriber, "SELECT count(*) FROM orders") == 1, "FULL identity delete")
        return {"physical_ddl": True, "logical_ddl_automatic": False, "sequence_collision": sequence_collision, "primary_sequence": primary_sequence, "subscriber_sequence": subscriber_sequence, "identity_rejected": identity_rejected, "full_identity_rows": [[2, "full identity"]]}


if __name__ == "__main__":
    print(json.dumps(experiment()))
