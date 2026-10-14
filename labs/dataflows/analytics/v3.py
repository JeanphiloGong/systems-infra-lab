"""Observe a cross-source mismatch, catch-up, and real source process outage."""
import json
import psycopg
from labs.dataflows.analytics.pg import (
    COPIED_REPORT, FEDERATED_REPORT, compose, configure_federation, connect,
    copied_report, load, measure, nodes, provenance, reset,
)


def experiment():
    reset()
    configure_federation()
    load("orders", "b1")
    load("customers", "b1")
    initial = copied_report()
    # Business change spans independent commits: an order references a new customer.
    with connect("orders") as db:
        db.execute("UPDATE orders SET customer_id=101,revision=101 WHERE id=1")
    mismatch = measure(FEDERATED_REPORT)
    assert mismatch["rows"] == [("C2", 20), ("C3", 30)]
    with connect("warehouse") as db:
        orphan = db.execute("SELECT o.id FROM remote_orders.orders o LEFT JOIN remote_customers.customers c ON c.id=o.customer_id WHERE c.id IS NULL").fetchall()
    assert orphan == [(1,)]
    with connect("customers") as db:
        db.execute("INSERT INTO customers VALUES (101,'C1new','west',101)")
    converged = measure(FEDERATED_REPORT)
    assert converged["rows"] == [("C1new", 10), ("C2", 20), ("C3", 30)]
    assert copied_report() == initial
    stale_cutoffs = provenance()
    with connect("warehouse") as db:
        servers_before = db.execute("SELECT srvname,srvoptions FROM pg_foreign_server ORDER BY srvname").fetchall()
        local_plan = db.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + COPIED_REPORT).fetchone()[0][0]
    local_nodes = list(nodes(local_plan["Plan"]))
    assert not any(n["Node Type"] == "Foreign Scan" for n in local_nodes)
    local_scanned = sum((n["Actual Rows"] + n.get("Rows Removed by Filter", 0)) * n["Actual Loops"]
                        for n in local_nodes if n["Node Type"] == "Seq Scan")
    stopped = False
    try:
        compose("stop", "customers")
        stopped = True
        try:
            measure(FEDERATED_REPORT)
        except psycopg.Error as error:
            outage_sqlstate = error.sqlstate
        else:
            raise AssertionError("federation succeeded with stopped source")
        assert copied_report() == initial
        with connect("warehouse") as db:
            assert db.execute("SELECT srvname,srvoptions FROM pg_foreign_server ORDER BY srvname").fetchall() == servers_before
    finally:
        if stopped:
            compose("up", "-d", "--wait", "customers")
    assert measure(FEDERATED_REPORT)["rows"] == converged["rows"]
    load("orders", "b2")
    load("customers", "b2")
    assert copied_report() == converged["rows"]
    return dict(initial=initial, mismatch=mismatch, orphan_orders=orphan,
                converged=converged, stale_warehouse_cutoffs=stale_cutoffs,
                caught_up_cutoffs=provenance(), outage_sqlstate=outage_sqlstate,
                connector_config_preserved=True, warehouse_remote_rows_per_read=0,
                local_scan=local_scanned,
                local_execution_ms=local_plan["Execution Time"])


if __name__ == "__main__":
    print(json.dumps(experiment()))
