import os

import pytest


@pytest.mark.postgres
def test_postgres_probe_requires_explicit_r04_environment() -> None:
    if os.getenv("A03_POSTGRES_LIVE") != "1":
        pytest.skip("set A03_POSTGRES_LIVE=1 with infra/r04.compose.yaml running")
    from labs.recovery.ha.postgres_probe import run

    result = run()
    assert result["replica_promoted"] is True
    assert result["old_primary_fence_required"] is True
