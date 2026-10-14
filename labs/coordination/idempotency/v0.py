from __future__ import annotations


class OrderService:
    def __init__(self) -> None:
        self.orders: list[str] = []

    def create_order(self, customer: str) -> str:
        order_id = f"order-{len(self.orders) + 1}"
        self.orders.append(order_id)
        return order_id


if __name__ == "__main__":
    service = OrderService()
    print(service.create_order("ada"))
    print(service.create_order("ada"))
