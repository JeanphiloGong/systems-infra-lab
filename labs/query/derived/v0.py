import json

from labs.query.derived.common import database, plan, summary


def run():
    with database() as (connection, _):
        query = "SELECT day,sum(amount) FROM sales GROUP BY day ORDER BY day"
        first = connection.execute(query).fetchall()
        second = connection.execute(query).fetchall()
        assert first == second == [(day, 10000) for day in range(30)]
        plans = [plan(connection, query), plan(connection, query)]
        return {"results": first, "queries": 2, "costs": [summary(p) for p in plans], "plans": plans}


if __name__ == "__main__":
    print(json.dumps(run()))
