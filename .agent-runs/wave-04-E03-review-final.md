# E03 independent review

Verdict: **pass** for v0-v4 after repair.

`uv run pytest tests/dataflows/events -q` returned **5 passed in 0.40s**. Each
version's complete source fence was extracted into a fresh directory and run by
a new interpreter.

v0 records the current-state history gap. v1 appends immutable ordered events,
replays valid order transitions and rejects invalid ones. v2 uses two
file-backed SQLite connections in a real concurrent race; exactly one expected-
version append wins and the other gets `Conflict`, without overwriting the
event stream. v3 persists processed keys, keeps duplicate delivery idempotent,
rejects skipped/out-of-order versions and rebuilds a lagging projection. v4
upcasts old payloads and keeps rebuild free of external side effects while an
explicit new-event dispatcher owns them.

The guide states the single-process SQLite and external-effect limitations. No
blocking findings; E03 v0-v4 are accepted.
