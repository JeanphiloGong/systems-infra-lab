# Wave 21 plan semantic fixes

Corrected the five concrete inconsistencies from
`.agent-runs/wave-20-remaining-plan-semantic-review.md`:

- D04 v1 now describes the actual file-backed close/reopen marker test and
  normal in-memory tutorial output, and explicitly leaves the effect-before-
  done-marker crash window unresolved.
- D04 v2 now states caller-supplied reverse order: refund position 2, then
  release position 1, with the exact idempotent effects.
- P03 v0 now depends on P01 routing concepts and its own complete initial
  Migration/checkpoint model, not a nonexistent prior migration version.
- P03 v2 limits pressure to append-ordered duplicate/tombstone replay and
  explicitly defers out-of-order delivery handling.
- E03 v2 now allows either concurrent writer to win; one append succeeds,
  one conflicts, and versions remain `[1,2]` without submission-order claims.

Targeted verification:

```text
$ uv run pytest tests/coordination/saga/test_d04.py::test_v1_restart_does_not_repeat_done_step tests/coordination/saga/test_d04.py::test_v2_reverse_compensation_is_idempotent -q
2 passed
$ uv run pytest tests/partitioning/migration/test_p03_migration.py::test_paused_copy_preserves_rows tests/partitioning/migration/test_p03_migration.py::test_delta_replay_is_idempotent -q
2 passed
$ uv run pytest 'tests/dataflows/events/test_e03_replay.py::test_exact_fence_replay[2]' -q
1 passed
```

These are documentation contract fixes; no implementation gap was hidden or
removed. No code, tutorial body, docs/progress, or index files were changed.
