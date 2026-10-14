"""Load both sources and reopen persisted provenance."""
import json
from labs.dataflows.analytics.pg import connect, copied_report, load, provenance, reset


def experiment():
    reset()
    assert load("orders", "b1") == load("customers", "b1") == 100
    report = copied_report()
    batches = provenance()
    assert report == [("C1", 10), ("C2", 20), ("C3", 30)]
    assert batches == [("customers", "b1", 100, 100), ("orders", "b1", 100, 100)]
    with connect("warehouse") as db:
        assert db.execute("SELECT count(*) FROM order_fact WHERE source_batch='b1'").fetchone()[0] == 100
        assert db.execute("SELECT count(*) FROM customer_dim WHERE source_batch='b1'").fetchone()[0] == 100
    return dict(report=report, batches=batches)


if __name__ == "__main__":
    print(json.dumps(experiment()))
