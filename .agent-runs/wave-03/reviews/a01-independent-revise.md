# A01 independent review: revise

The author evidence shows real PostgreSQL logical/custom dumps, `pg_restore`,
corruption detection, `pg_basebackup`, and WAL position markers. Those are useful
backup experiments, but the original roadmap A01 requires Point-in-Time Recovery:

- v2 configures a physical base backup and WAL archive and checks archive
  continuity;
- v3 restores an isolated instance to a precise point before an accidental
  delete;
- v4 recognizes missing archive or damaged backup during an actual recovery.

The implementation explicitly defers continuous WAL archiving,
`restore_command`, and a second recovery instance. A base-backup LSN marker and
a timestamp-vs-row demonstration do not prove PITR or the stated recovery
invariant. The version tutorials must add an isolated archive/restore workflow
(or revise the roadmap before implementation, which is out of scope here),
execute recovery on a separate PostgreSQL instance, and verify the deleted row
is present at the selected recovery target while later changes are absent.

Do not update progress or claim A01 accepted until the actual v0-v4 source fences
replay this behavior and the corrupted/missing archive failure is observed.
