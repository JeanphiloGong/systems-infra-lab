from __future__ import annotations

import json

from common import connect


def experiment() -> dict[str, object]:
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS source_orders, projection")
        conn.execute("CREATE TABLE source_orders(id int PRIMARY KEY, value text)")
        conn.execute("CREATE TABLE projection(id int PRIMARY KEY, value text)")
        conn.execute("INSERT INTO source_orders VALUES (1,'created')")
        try:
            conn.execute("INSERT INTO projection VALUES (1,'created')")
            raise ConnectionError("projection write failed after source write")
        except ConnectionError:
            pass
        assert conn.execute("SELECT count(*) FROM source_orders").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM projection").fetchone()[0] == 1
        conn.execute("DELETE FROM projection")
        return {"source_rows": 1, "projection_rows_after_failure": 0, "inconsistent": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
