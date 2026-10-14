import json

from labs.query.derived.common import database, plan, summary, total


def run():
    with database() as (c, _):
        c.execute("CREATE MATERIALIZED VIEW daily AS SELECT day,sum(amount) AS amount FROM sales GROUP BY day")
        before = int(c.execute("SELECT sum(amount) FROM daily").fetchone()[0])
        c.execute("INSERT INTO sales VALUES (30001,0,50)")
        stale = int(c.execute("SELECT sum(amount) FROM daily").fetchone()[0])
        fresh = total(c)
        assert before == stale == 300000 and fresh == 300050
        source = plan(c, "SELECT day,sum(amount) FROM sales GROUP BY day")
        derived = plan(c, "SELECT day,amount FROM daily")
        c.execute("REFRESH MATERIALIZED VIEW daily")
        assert c.execute("SELECT sum(amount) FROM daily").fetchone()[0] == fresh
        return {"before": before, "stale": stale, "source": fresh, "after_refresh": fresh,
                "costs": {"source": summary(source), "view": summary(derived)}, "plans": [source, derived]}


if __name__ == "__main__":
    print(json.dumps(run()))
