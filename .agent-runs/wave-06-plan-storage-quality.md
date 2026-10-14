# Wave 06 plan quality evidence: S/P/T

Scope was limited to `/home/gong/date/2026/oct/systems-infra-lab` and these
tutorial roots:

- `tutorials/01-storage-engines` (S01-S07)
- `tutorials/02-transactions-isolation` (T01-T04)
- `tutorials/03-partitioning-scaling` (P01-P03)

The audit covered 76 existing version plans. Plans that already contained the
required incremental structure were preserved. Affected plans received a
version-specific `Tutorial Increment` section with explicit:

`Pressure`, `Naive`, `Break`, `Change`, `Check`, `Freeze`, `Still-lacks`, and
`Next` fields.

The section text is grounded in each module's actual scenario and tutorial
opening, and its check names the module's existing pytest path. P03 v0-v4
already had complete sections and were not duplicated.

```text
$ python3 ... field/path audit ...
plans_checked 76
missing []
bad_commands []

$ uv run python tests/partitioning/migration/replay_p03.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok

$ uv run pytest tests/partitioning/migration -q
3 passed
```

No `docs/progress.md`, tutorial indexes, F01 connection plans, or replication
plans were changed. F01 lives at `tutorials/01-storage-engines/07-connections`
and is outside this S/P/T batch.
