"""Measure a real postgres_fdw join across two independently queried sources."""
import json
from labs.dataflows.analytics.pg import FEDERATED_REPORT, configure_federation, connect, measure, reset


def experiment():
    reset()
    configure_federation()
    baseline = measure("SELECT id,customer_id,amount FROM remote_orders.orders")
    baseline_customers = measure("SELECT id,name FROM remote_customers.customers")
    selective = measure(FEDERATED_REPORT)
    assert selective["rows"] == [("C1", 10), ("C2", 20), ("C3", 30)]
    assert {s["source"] for s in selective["sources"]} == {"orders", "customers"}
    for sample in selective["sources"]:
        assert "WHERE" in sample["sql"] and "west" in sample["sql"]
        assert sample["scanned"] == 100 and sample["transferred"] == 3
    full = baseline["sources"] + baseline_customers["sources"]
    assert sum(s["transferred"] for s in full) == 200
    with connect("warehouse") as db:
        extension = db.execute("SELECT extversion FROM pg_extension WHERE extname='postgres_fdw'").fetchone()[0]
        server_version = db.execute("SHOW server_version").fetchone()[0]
    return dict(postgres=server_version, postgres_fdw=extension, full=full, selective=selective)


if __name__ == "__main__":
    print(json.dumps(experiment()))
