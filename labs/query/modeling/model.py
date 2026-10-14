from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderLine:
    order_id: int
    customer_id: int
    product_id: int
    purchased_price: int
    quantity: int


class NormalizedModel:
    def __init__(self) -> None:
        self.customers: dict[int, str] = {}
        self.products: dict[int, str] = {}
        self.orders: dict[int, tuple[int, int]] = {}
        self.lines: dict[int, OrderLine] = {}

    def customer(self, customer_id: int, name: str) -> None:
        self.customers[customer_id] = name

    def product(self, product_id: int, name: str) -> None:
        self.products[product_id] = name

    def order(self, line: OrderLine) -> None:
        if line.customer_id not in self.customers or line.product_id not in self.products:
            raise KeyError("foreign key missing")
        self.orders[line.order_id] = (line.customer_id, line.product_id)
        self.lines[line.order_id] = line

    def read(self, order_id: int) -> dict[str, object]:
        line = self.lines[order_id]
        return {"order_id": order_id, "customer": self.customers[line.customer_id], "product": self.products[line.product_id], "price": line.purchased_price}


class ReadModel:
    def __init__(self) -> None:
        self.rows: dict[int, dict[str, object]] = {}
        self.writes = 0

    def rebuild(self, normalized: NormalizedModel) -> None:
        self.rows.clear()
        for order_id in normalized.lines:
            self.rows[order_id] = normalized.read(order_id)
            self.writes += 1

    def update_product_name(self, product: str, normalized: NormalizedModel) -> None:
        for row in self.rows.values():
            if row["product"] == product:
                row["product"] = normalized.products[next(pid for pid, name in normalized.products.items() if name == product)]
                self.writes += 1
