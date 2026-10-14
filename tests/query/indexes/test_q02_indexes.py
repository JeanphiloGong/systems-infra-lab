from labs.query.indexes.model import Row, Table


def table() -> Table:
    return Table([Row(user % 3, user, user, user * 10) for user in range(12)])


def test_index_preserves_results_and_reduces_candidates() -> None:
    model = table(); before, _ = model.query(1); model.build_index(); after, metrics = model.query(1)
    assert before == after and metrics["index_entries"] == 4


def test_composite_index_and_index_only_visibility() -> None:
    model = table(); model.build_index(("user", "day")); result, metrics = model.query(1, 4, covering=True); assert result and metrics["heap_fetches"] == 0
    model.update(4, 999); _, changed = model.query(1, 4, covering=True); assert changed["heap_fetches"] == 1
