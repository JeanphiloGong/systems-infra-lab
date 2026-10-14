import json

from labs.query.derived.cache import Cache
from labs.query.derived.common import database, total


def run():
    with database() as (c, _):
        now = [0.0]
        cache = Cache(lambda: now[0])
        assert cache.get(lambda: total(c)) == 300000
        assert cache.get(lambda: total(c)) == 300000
        c.execute("INSERT INTO sales VALUES (30001,0,50)")
        now[0] = 4.999
        assert cache.get(lambda: total(c)) == 300000
        now[0] = 5
        assert cache.get(lambda: total(c)) == 300050
        assert (cache.loads, cache.hits) == (2, 2)
        return {"source_loads": cache.loads, "cache_hits": cache.hits,
                "old_before_ttl": 300000, "at_expiry": 300050, "ttl_seconds": 5}


if __name__ == "__main__":
    print(json.dumps(run()))
