# Wave 01 review readiness

Scope: S01 v0-v4 and T01 v0-v4. This is a roadmap audit, not approval of
unwritten tutorials or experiments.

Reviewed sources: `docs/roadmap.md`, `from-scratch-tutorial-review/SKILL.md`,
and its `references/quality-standards.md`.

## Findings

No blocking dependency cycle found for these two modules. Their detailed
plans and actual checkpoints must still be reviewed before acceptance.

Required implementation checks derived from the roadmap:

- `docs/roadmap.md:133`: direct offsets require an explicit relationship
  between record ID and physical slot. Fixed record length alone does not
  locate an arbitrary business key.
- `docs/roadmap.md:134`: test first and last slots of adjacent pages and the
  incomplete final page. Reject truncated records explicitly.
- `docs/roadmap.md:135`: record access count, distinct page count, and latency
  distributions for reproducible workloads. Application read byte counts
  cannot be described as physical device reads.
- `docs/roadmap.md:136`: bounded cache tests must prove eviction and correct
  reload, and measurements must distinguish application and OS caches.
- `docs/roadmap.md:241`: validate missing/invalid target without persisting a
  debit; broken baseline must explicitly use autocommit, repaired checkpoint
  must roll back both updates. Verify stored balances through a fresh read.
- `docs/roadmap.md:242`: execute READ UNCOMMITTED explicitly and explain that
  PostgreSQL implements it as READ COMMITTED. Do not simulate a dirty read and
  describe it as PostgreSQL behavior.
- `docs/roadmap.md:243`: retain one reader transaction, with a committed
  transfer between its two SELECT statements, to demonstrate read skew.
- `docs/roadmap.md:244`: repeat the same range in the same transaction on
  either side of another connection's committed insertion; establish the
  REPEATABLE READ snapshot with the first SELECT, not merely BEGIN.
- `docs/roadmap.md:245`: separate atomicity evidence, declared constraints,
  isolation observations, and durability assumptions. These experiments do
  not prove all ACID properties or power-loss durability.

## Acceptance protocol

Inspect each version's concrete plan, pressure trace, code changes, complete
assembled checkpoint, setup, expected results, failure checks, and deferred
scope. Replay reader-visible commands independently and compare extracted
checkpoint code with delivered code. Passing only the final module test suite
is insufficient to accept earlier tutorial versions.

## Verdict

Roadmap ready for implementation. No version accepted yet; actual tutorial
and executable evidence pending.
