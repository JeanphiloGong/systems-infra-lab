# Q02 plan

Follow a real PostgreSQL query for recent user orders from a scan to a secondary index, a composite key, and an index-only visibility boundary. The live driver is `labs/query/indexes/postgres.py`; the older Python Table model is explanatory only.

1. v0 creates 100,000 rows in a unique schema and records full EXPLAIN ANALYZE BUFFERS JSON for an unindexed lookup. Assert 100 results and 99,900 filtered rows.
2. v1 creates a user index and compares rare versus common user predicates. Verify an indexed rare lookup and common-value sequential scan, with identical selective results before/after indexing.
3. v2 compares both B-tree column orders on the exact same user/time-range/ORDER BY/LIMIT SQL. Assert result equality and record differing buffer access counts.
4. v3 uses an INCLUDE covering index, VACUUM, UPDATE, and VACUUM again. Assert Index Only Scan plus Heap Fetches changing from zero to positive to zero; verify actual updated values.

All checkpoints print the complete live driver. Strict replay extracts it into a temporary directory and fails without the real database DSN. Each experiment removes its isolated schema in finally. Run against the repository's pinned PostgreSQL 16 service; other versions/settings may legitimately choose different plans. Buffers and heap fetches describe database accesses, not physical device I/O or arbitrary logical counters.
