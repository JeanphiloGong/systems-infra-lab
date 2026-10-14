import os

import pytest


@pytest.mark.postgres
def test_patroni_probe_requires_explicit_live_environment() -> None:
    if os.getenv("A03_PATRONI_LIVE") != "1":
        pytest.skip("set A03_PATRONI_LIVE=1 with infra/a03-patroni running")

    from labs.recovery.ha.patroni_probe import run

    result = run()
    assert result["acknowledged_lost"] == 0
    assert result["old_process_alive"] is True
    assert result["old_write_rejected"] is True
    assert result["rejoin"] == "basebackup via Patroni reinitialize"
