# Wave 02 reopened findings

## Findings

- [revise] S02 v7 tutorial claims boundary experiments should report logical
  page/node access and save-time truncation/CRC failure, but its printed checks
  only insert, scan, delete, and validate. There is no actual page-access
  counter, save interruption, CRC corruption, or truncated-file command in the
  v7 guide. Add executable failure/access experiments before calling the scope
  complete. The complete fences are present and replayable; this is a missing
  evidence/claim finding, not a missing-source finding.
- [revise] T04 v2 `retry_once` uses an unbounded `while True` and has no retry
  limit, backoff, or test that a real serialization failure enters the retry
  path. Its documented clean `--retry` command returns `(0, True)`, which does
  not demonstrate retry behavior. Either bound and exercise it, or narrow the
  teaching claim to “fresh transaction path” and defer failure injection.

## Independent printed-code verification

Extracted each T04 fence and embedded SQL schema into a new temporary package,
without importing repository implementation. Ran:

- T04 v1 CLI: `(1, 1)`.
- T04 v2 `--retry`: `(0, True)`.
- T04 v3 `--metrics`: dictionary with `aborted: 1`, `remaining: 1`, and a
  positive `elapsed_seconds`.

The current focused T04 suite passed 3 tests. These results prove the printed
entry points run, but they do not prove T04 v2 retries an actual aborted
transaction, and they do not cover S02 v7's claimed save-failure experiment.

Prior S02 v0-v6 and T04 v0-v1/v2 checkpoint findings remain in their earlier
records; this file reopens only the two scope/evidence gaps above.
