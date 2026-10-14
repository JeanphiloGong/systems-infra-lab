import os

import pytest

from labs.query.planner.postgres import run


@pytest.mark.postgres
@pytest.mark.skipif(not os.getenv("SYSTEMS_LAB_DATABASE_URL"), reason="requires isolated PostgreSQL")
@pytest.mark.parametrize("version", range(4))
def test_live_experiment(version):
    result = run(version)
    assert result["server"] >= 160000
    assert result["block_size"] > 0
    assert all(item["actual_rows"] > 0 for item in result["metrics"].values())
