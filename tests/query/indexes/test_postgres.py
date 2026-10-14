import os

import pytest

from labs.query.indexes.postgres import run


@pytest.mark.postgres
@pytest.mark.skipif(not os.getenv("SYSTEMS_LAB_DATABASE_URL"), reason="requires isolated PostgreSQL")
@pytest.mark.parametrize("version", range(4))
def test_live_checkpoint(version):
    result = run(version)
    assert result["metrics"]["baseline"]["actual_rows"] == 100
    assert result["plans"]["baseline"]["Plan"]["Plans"][0]["Rows Removed by Filter"] == 99900
    if version == 3:
        assert result["metrics"]["visible"]["heap_fetches"] == 0
        assert result["metrics"]["updated"]["heap_fetches"] > 0
        assert result["metrics"]["vacuumed"]["heap_fetches"] == 0
