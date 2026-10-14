# P03 v4 rereview

Verdict: not accepted yet.

The revised checkpoint now writes a JSON state file and launches a fresh child
process, which is a useful restart boundary. However, the child does not
reconstruct `Migration` or invoke its real owner/fence/write methods. It only
checks the numeric token with an inline conditional and then directly mutates
`state['shards']['b']['9']`. Consequently the printed code does not prove
that an old-owner write is rejected or that a current-owner write succeeds
through the migration protocol. The persisted state also omits the migration
log, sequence, paused/phase state needed to resume an interrupted copy.

Independent checks remain green but are insufficient for the claimed scope:

```text
uv run pytest tests/partitioning/migration -q
3 passed
uv run python tests/partitioning/migration/replay_p03.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
```

No reviewer source or tutorial edits were made.
