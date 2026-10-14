# Q03 independent original PostgreSQL scope review

Verdict: PASS for the repaired original experiment scope at `docs/roadmap.md:520`. This supersedes earlier simulation-only acceptance and resolves the Q03 portion of `q02-q03-original-scope-reopened.md`. No blocking findings.

Read actual PostgreSQL source, all four tutorial explanations, replay isolation and tests. With the isolated `SYSTEMS_LAB_DATABASE_URL`, actually ran:

- `uv run pytest tests/query/planner -q`: **7 passed in 4.18s**, including four live PostgreSQL cases.
- `uv run python tests/query/planner/replay_q03.py`: **all four version-specific extracted checkpoints passed** on PostgreSQL **160014**. Each standalone fence executes in a new temporary directory/interpreter with its own PYTHONPATH; no worktree planner import supplies missing behavior.

## Actual observations

| Version | Measured evidence |
| --- | --- |
| v0 | 20-row table Seq Scan returns1; 100,000-row table Bitmap Heap/Index Scan returns100; reference tuples checked |
| v1 stale | Bitmap Heap/Index Scan estimates190, returns90,010 |
| v1 ANALYZE | Seq Scan estimates90,163, returns90,010; complete sorted result unchanged |
| v2 rare | Independent estimate2 -> extended estimate500, actual500 |
| v2 hot | Independent estimate25,000 -> extended estimate50,000, actual50,000 |
| v3 nested | 40,000 equal-result join pairs; Memoize40,000 loops, inner index2,000 loops;7,482 buffer hits;35.267ms elapsed |
| v3 hash | Same40,000 join pairs;1,491 buffer hits;87kB hash memory,1 batch;20.504ms elapsed |
| v3 low-memory sort | Real external merge,10,792kB disk;5,376 temp blocks read and5,656 written;177.028ms |
| v3 high-memory sort | Quicksort,12,787kB memory,zero temp reads/writes;124.301ms |

v2 really creates dependencies/MCV statistics and executes ANALYZE. Actual row counts stay unchanged for both predicates, and complete rare results are compared. v3 really changes work_mem and executes full wide-row sorts; sorted outputs are checked against the same complete reference, rather than labeling an in-memory Python sort as spilled.

## Provenance and boundaries

Metrics are projected from EXPLAIN ANALYZE BUFFERS SETTINGS JSON. Full plans are retained. Root buffer counters are inclusive and not summed over children. Temporary blocks are cumulative database-layer I/O, not peak space or guaranteed device traffic. Sort memory/disk and hash memory are actual operator observations.

The CPU portion of the lesson is explicitly analysis of operator work and planner assumptions, not measurement of CPU milliseconds. EXPLAIN elapsed time is not CPU time; cpu_* costs are not measurements. The tutorial states this limitation and relates repeated probes/hash work/spill to resource costs without fabricating counters. Separate CPU profiling is not performed.

Join enable_* flags deliberately select diagnostic alternatives, and the text does not claim those alternatives were automatic cost-based choices. v0/v1 access-path decisions are observed on the pinned fixture. Exact timings are not acceptance assertions. v1's refreshed plan was slower in this warm run despite a better estimate, consistent with the text's warning against a universal speedup claim.

Each run owns a unique temporary schema and drops only that schema in finally; session settings disappear on connection close. No production planner or cross-version performance guarantee is established.

Review artifact only; no implementation abstraction or source cleanup added.
