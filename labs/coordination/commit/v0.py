from __future__ import annotations

import json
import psycopg

from pg import balances, resources


def experiment() -> dict[str, object]:
    with resources() as dsns:
        with psycopg.connect(dsns[0]) as source:
            source.execute("UPDATE account SET balance = balance - 30 WHERE id = 1")
        try:
            with psycopg.connect(dsns[1]) as target:
                target.execute("UPDATE account SET balance = balance + 30 WHERE id = 1")
                raise RuntimeError("second database fails before commit")
        except RuntimeError:
            pass
        result = balances(dsns)
        assert result == [70, 100]
        return {"balances": result, "total": sum(result)}


if __name__ == "__main__":
    print(json.dumps(experiment()))
