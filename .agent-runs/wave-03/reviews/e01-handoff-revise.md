# E01 source-position repair review

Verdict: revise. Independent reviewer: root (not E01 author).

## Verified improvements

The dedicated PostgreSQL 16 stack was started with `docker compose -f
infra/e01.compose.yaml up -d --wait`. With E01_DATABASE_URL set to its dedicated
DSN, `uv run pytest tests/dataflows/cdc -q` returned **6 passed in 3.29s**.
Those tests include extracted tutorial replay. Real LSNs replace synthetic zero
positions. v3 now uses persistent SQLite and fresh subprocess exits before target
commit and after commit/before source acknowledgment. These are substantive repairs.

## Blocking original-scope gap

Roadmap E01 describes order updates and committed INSERT/UPDATE/DELETE, with
no missing events at the snapshot/increment boundary. v2 still ignores all
UPDATE/DELETE and skips an INSERT forever if its key was in the snapshot.
v3 likewise only applies INSERT. The added limitation paragraph does not satisfy
the original order-update scenario or its no-omission invariant.

Actual probe: `uv run python .agent-runs/wave-03/reviews/e01_handoff_probe.py`.
The probe executes the author's v2 code with exactly one extra write after its
snapshot and before its existing second INSERT. Both original assertions pass:

- UPDATE id=1 to paid: projection remains before-snapshot; actual source is paid.
- DELETE id=1: projection retains id=1; actual source no longer contains it.

Required repair: carry insert/update/delete semantics through snapshot handoff
and durable target application. Identify an exact cut or a documented protocol
that safely handles snapshot overlap, transaction commit order and concurrent
writes. Test updates, deletes and delete/reinsert across the cut, then reproduce
the same stream after commit-boundary crashes in v3. Key-only deduplication is
not event deduplication. Preserve the existing real peek/commit/ack behavior.

Also replace whitespace/quote trimming of test_decoding values with a supported
structured decoder or a parser with an explicit verified contract: values such
as 'paid in full' currently truncate in v2. Do not turn this into an unexplained
production connector claim.

No implementation code changed by reviewer. The probe is permanent review
evidence, not a runtime abstraction; dedicated service cleanup was requested
after verification. No progress acceptance or Git commit performed.
