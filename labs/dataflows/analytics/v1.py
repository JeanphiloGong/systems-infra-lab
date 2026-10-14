"""Repeat source-scoped batches; apply late order and customer corrections."""
import json
from labs.dataflows.analytics.pg import connect, copied_report, load, provenance, reset


def experiment():
    reset()
    load("orders", "b1")
    load("customers", "b1")
    before = provenance()
    assert load("orders", "b1") == load("customers", "b1") == 0
    assert provenance() == before
    initial = copied_report()
    with connect("orders") as db:
        db.execute("UPDATE orders SET amount=35,customer_id=2,revision=101 WHERE id=1")
    with connect("customers") as db:
        db.execute("UPDATE customers SET name='C2-corrected',revision=101 WHERE id=2")
    assert load("orders", "b2") == load("customers", "b2") == 1
    corrected = copied_report()
    assert corrected == [("C2-corrected", 55), ("C3", 30)]
    batches = provenance()
    assert batches == [("customers", "b1", 100, 100), ("customers", "b2", 101, 1),
                       ("orders", "b1", 100, 100), ("orders", "b2", 101, 1)]
    assert load("orders", "b2") == load("customers", "b2") == 0
    assert provenance() == batches and copied_report() == corrected
    with connect("warehouse") as db:
        assert db.execute("SELECT business_day,revision,source_batch FROM order_fact WHERE id=1").fetchone() == (1, 101, "b2")
        assert db.execute("SELECT source_batch FROM customer_dim WHERE id=2").fetchone() == ("b2",)
        assert db.execute("SELECT count(*) FROM order_fact").fetchone()[0] == 100
    return dict(initial=initial, corrected=corrected, replayed=copied_report(), batches=batches)


if __name__ == "__main__":
    print(json.dumps(experiment()))
