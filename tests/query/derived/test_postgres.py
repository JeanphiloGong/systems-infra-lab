import importlib
import os

import pytest

from labs.query.derived.cache import Cache


@pytest.mark.postgres
@pytest.mark.skipif(not os.getenv("SYSTEMS_LAB_DATABASE_URL"), reason="requires isolated PostgreSQL")
@pytest.mark.parametrize("version", range(5))
def test_live_checkpoint(version):
    assert importlib.import_module(f"labs.query.derived.v{version}").run()


def test_failed_load_is_not_cached():
    cache = Cache(lambda: 0)
    def fail():
        raise RuntimeError("source unavailable")
    with pytest.raises(RuntimeError):
        cache.get(fail)
    assert cache.entry is None
    assert cache.get(lambda: 12) == 12


def test_exact_expiry_and_invalid_ttl():
    now = [0]
    cache = Cache(lambda: now[0], ttl=1)
    assert cache.get(lambda: "old") == "old"
    now[0] = 1
    assert cache.get(lambda: "new") == "new"
    with pytest.raises(ValueError):
        Cache(lambda: 0, ttl=0)
