from __future__ import annotations

import json
import psycopg

from common import connect, scalar, wait_for


def experiment() -> dict[str, object]:
    with connect("primary") as primary, connect("standby") as standby:
        assert str(scalar(primary, "SHOW server_version")).startswith("16.")
        assert scalar(standby, "SELECT pg_is_in_recovery()") is True
        primary.execute("DROP TABLE IF EXISTS physical_probe")
        primary.execute("CREATE TABLE physical_probe (id int PRIMARY KEY, value text)")
        primary.execute("INSERT INTO physical_probe VALUES (1,'streamed')")
        target = str(scalar(primary, "SELECT pg_current_wal_lsn()"))
        wait_for(lambda: standby.execute("SELECT pg_last_wal_replay_lsn() >= %s::pg_lsn", (target,)).fetchone()[0], "standby replay")
        assert standby.execute("SELECT * FROM physical_probe").fetchall() == [(1, "streamed")]
        try:
            standby.execute("INSERT INTO physical_probe VALUES (2,'forbidden')")
        except psycopg.errors.ReadOnlySqlTransaction:
            readonly = True
        else:
            raise AssertionError("standby accepted write")
        senders = primary.execute("SELECT application_name,state,sync_state FROM pg_stat_replication WHERE application_name='r04_standby'").fetchall()
        assert senders and senders[0][1] == "streaming"
        return {"rows": 1, "read_only": readonly, "target_lsn": target, "senders": senders}


if __name__ == "__main__":
    print(json.dumps(experiment()))
