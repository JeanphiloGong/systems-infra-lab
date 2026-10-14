# T04 v2 final review

## Verdict

pass

The current printed checkpoint defines `max_retries=3`, increments the retry
counter only after a serialization failure, and raises once the bound is
exceeded. The prose now explicitly limits the documented `--retry` command to
the clean no-contention path; the concurrent abort remains the v1 experiment.
It does not claim that the clean command proves a retry occurred.

## Verification

Extracted the current `serializable.py` and embedded schema into a new
temporary package, without importing repository source, and ran:

```text
uv run python -m labs.transactions.serializable.serializable --retry
(0, True)
```

The checkpoint exited successfully and matched the documented no-contention
result. Current document SHA-256:
`56a8ff2dfee070b8b3af25c67c7a2afaa196c7513f4eb586ae5fc92ace776244`.

The v1 concurrent test remains the evidence for an actual serialization abort;
this version teaches the bounded fresh-transaction retry path but does not
pretend its clean CLI invocation injects contention.
