# Q03 plan

Use the actual PostgreSQL 16 optimizer and executor; the older Python cost model is explanatory only. Each guide prints a version-specific complete program and strict replay extracts that exact program into a temporary directory. Each live run creates and removes its own schema.

1. v0: compare the same indexed predicate at 20 and 100,000 rows; assert sequential versus indexed access and reference-result equality.
2. v1: ANALYZE a uniform dataset, introduce a hotspot without refreshing column statistics, then compare identical SQL before/after ANALYZE. Assert improved row estimate and changed access path without asserting a timing speedup.
3. v2: create correlated city/zip data with one hot pair; compare rare and hot equality predicates before/after dependencies+MCV extended statistics. Assert estimate improvements and unchanged actual results.
4. v3: deliberately expose nested-loop and hash alternatives for identical join SQL; compare result sets and actual loops/memory/buffers. Sort identical wide rows at two work_mem values; assert real external spill/temp I/O versus in-memory sort without spill.

Full EXPLAIN ANALYZE BUFFERS SETTINGS JSON and server version are returned. PostgreSQL CPU cost parameters are estimates, actual loop/row work is reported, and wall-clock execution time is measured. Core EXPLAIN does not measure CPU time separately; no fabricated CPU metric is used. Temporary-block counters and Sort Space Used are measured database I/O and space metrics, not hardware performance claims.
