# T04 build evidence

Real PostgreSQL `SERIALIZABLE` Barrier experiment implemented; one transaction aborts deterministically. Bounded whole-transaction retry (`max_retries=3`) and connected `measure_once` metrics are present. `SYSTEMS_LAB_DATABASE_URL=... uv run python -m pytest tests/transactions/serializable -q` -> **3 passed in 0.40s** (abort, retry, printed checkpoint boundary replay). v1 printed source excludes retry; v2 includes retry; v3 includes measure_once. No commits; independent review pending.
