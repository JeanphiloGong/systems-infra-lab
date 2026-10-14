# E04 original-scope review: REVISE

Authority: docs/roadmap.md E04 v0-v3. The earlier review only identified a dead
branch and missed these original requirements. Removing that branch does not
make the module acceptable.

1. v0 creates customers.db but never reads its rows or loads a customer dimension.
   Only order rows enter the warehouse. The promised two-source import and
   customer/order analysis are absent. Batch provenance is only recorded for
   orders, with an assumed watermark of 2.
2. v2 attaches a single local SQLite file. `remote_rows=3` and `source_rows=100`
   are literal constants, not scan measurements. A local B-tree SEARCH plan does
   not prove remote predicate pushdown. Implement a fixed connector with two
   independently queryable sources, inspect the remote query/plan and measure
   transferred/scanned rows using a declared method. A PostgreSQL postgres_fdw
   coordinator with two dedicated source databases is an available option.
3. v3 only compares one source against a copy, then removes its query binding
   using DETACH. It never creates two independently evolving sources or measures
   the requested cost/freshness tradeoff. Inject a source outage while preserving
   the connector configuration, observe federated failure and copied availability,
   and demonstrate a mismatched cross-source report before both sources catch up.
4. v1 uses a source table inside the warehouse and no longer grows v0's two-source
   import. Preserve the source/batch lineage across versions and execute an actual
   repeated batch plus late correction with assertions on persisted provenance.

All four complete fences must include their actual supporting files and
configuration. Isolated replay must exercise the respective version's original
requirements; hardcoded output labels are not evidence. E04 remains unaccepted.
