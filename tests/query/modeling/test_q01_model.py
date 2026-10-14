import pytest

from labs.query.modeling.model import NormalizedModel, OrderLine, ReadModel


def seeded() -> NormalizedModel:
    model = NormalizedModel(); model.customer(1, "Ada"); model.product(7, "Widget")
    model.order(OrderLine(10, 1, 7, 12, 2)); return model


def test_normalized_update_changes_current_name_not_historical_price() -> None:
    model = seeded(); model.products[7] = "New Widget"
    assert model.read(10)["product"] == "New Widget" and model.read(10)["price"] == 12


def test_foreign_keys_are_required() -> None:
    model = NormalizedModel()
    with pytest.raises(KeyError): model.order(OrderLine(1, 9, 7, 1, 1))


def test_read_model_can_lag_and_rebuild() -> None:
    model = seeded(); view = ReadModel(); view.rebuild(model); model.products[7] = "New Widget"
    assert view.rows[10]["product"] == "Widget"
    view.rebuild(model); assert view.rows[10]["product"] == "New Widget"


def test_purchase_price_is_immutable_per_order() -> None:
    model = seeded()
    model.order(OrderLine(11, 1, 7, 13, 1))
    assert model.lines[10].purchased_price == 12
    assert model.lines[11].purchased_price == 13
