# E02 independent review: revise

The dedicated PostgreSQL 16 replay currently passes **5 tests in 1.50s**, and
the source fences match the implementation. v0 correctly demonstrates a
breaking rename; v1 demonstrates additive nullable schema and dual write; v3
demonstrates final `NOT NULL` and legacy-column removal.

## Blocking gap

Roadmap E02 v2 requires verification of repeated execution, partial failure,
and progress recovery. `backfill(stop_after=2)` is a normal return from the same
Python process. No child process exits during or between batches, and no fresh
process reopens the database before resuming. The tests therefore prove a clean
pause, not a partial failure boundary. The prose says “进程中断后” but the
checkpoint is not tested across an interrupted process.

Required repair: add a deterministic worker/failpoint that commits the first
batch, exits at a declared boundary, and a fresh worker resumes from the
persistent PostgreSQL checkpoint. Verify the committed rows and checkpoint
survive, an uncommitted batch leaves no partial update, repeated fresh-worker
execution performs zero work, and a new-client write protected by
`full_name IS NULL` is not overwritten. Keep the complete source fence and
isolated PostgreSQL replay.

This is a real-scope finding, not a request for more output assertions. No
progress acceptance or commit performed.
