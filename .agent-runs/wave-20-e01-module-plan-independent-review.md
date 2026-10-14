# Wave-20 independent module-plan review: E01

## Source contract check

The revised `tutorials/08-dataflows/01-cdc/plan.md` accurately describes the
module's snapshot boundary and v3 limitation.

- `labs/dataflows/cdc/common.py:snapshot_cut` opens a transaction, executes
  `LOCK TABLE orders IN SHARE MODE`, reads the ordered snapshot, consumes the
  slot events that overlap the snapshot, and reads `confirmed_flush_lsn`
  before the transaction closes. PostgreSQL's SHARE table lock conflicts with
  writers' row-exclusive operations, so the documented short write block is a
  real property of this implementation.
- `labs/dataflows/cdc/v2.py` performs the post-cut mixed tail as UPDATE,
  DELETE, DELETE, INSERT, INSERT, applies DELETE as removal and the later
  same-ID INSERT as a new row, then compares the projection with the source.
  Its assertion also requires the final source position to be greater than the
  snapshot cursor. The module plan's v2 description therefore matches both the
  mechanism and observable result.
- `labs/dataflows/cdc/v3.py` initializes the projection from `snapshot_cut`
  and writes those snapshot rows before its worker checkpoint transaction.
  The crash tests cover the incremental projection/checkpoint transaction and
  acknowledge the slot only after target commit. The plan explicitly limits v3
  to an already initialized snapshot and says first-snapshot/cursor atomic
  publication is out of scope; this matches the source rather than claiming
  end-to-end initialization atomicity.

## Verdict

**PASS.** The module-level plan closes the snapshot-lock and mixed-operation
coverage gap and accurately preserves the v3 initialization boundary. This was
a source/documentation review only; no PostgreSQL service was started and no
implementation, tutorial, index, or progress file was changed.
