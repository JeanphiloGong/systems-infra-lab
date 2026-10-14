from labs.partitioning.routing.single import get_order, put_order, scan_orders


def test_overwrite_and_missing() -> None:
    orders: dict[int, str] = {}
    assert get_order(orders, 1) is None
    put_order(orders, 1, "created")
    put_order(orders, 1, "paid")
    assert get_order(orders, 1) == "paid"
    assert len(orders) == 1


def test_range_is_sorted_and_half_open() -> None:
    orders = {20: "paid", 5: "created", 10: "shipped"}
    assert scan_orders(orders, 5, 20) == [(5, "created"), (10, "shipped")]
    assert scan_orders(orders, 10, 10) == []
    assert scan_orders(orders, 99, 100) == []
