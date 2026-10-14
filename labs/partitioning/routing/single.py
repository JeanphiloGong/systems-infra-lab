def put_order(orders: dict[int, str], order_id: int, status: str) -> None:
    orders[order_id] = status


def get_order(orders: dict[int, str], order_id: int) -> str | None:
    return orders.get(order_id)


def scan_orders(orders: dict[int, str], start: int, stop: int) -> list[tuple[int, str]]:
    return sorted((key, value) for key, value in orders.items() if start <= key < stop)
