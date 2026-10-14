from __future__ import annotations


class Services:
    def __init__(self) -> None:
        self.inventory: set[str] = set()
        self.charged: set[str] = set()
        self.shipments: set[str] = set()

    def reserve(self, order: str) -> None:
        self.inventory.add(order)

    def charge(self, order: str) -> None:
        self.charged.add(order)

    def ship(self, order: str, fail: bool = False) -> None:
        if fail:
            raise RuntimeError("delivery unavailable")
        self.shipments.add(order)


def create_order(services: Services, order: str, fail_delivery: bool = False) -> str:
    services.reserve(order)
    services.charge(order)
    services.ship(order, fail_delivery)
    return "completed"


if __name__ == "__main__":
    services = Services()
    try:
        create_order(services, "order-1", fail_delivery=True)
    except RuntimeError:
        pass
    print({"inventory": services.inventory, "charged": services.charged, "shipments": services.shipments})
