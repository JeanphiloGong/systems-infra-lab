# D02 and C01 independent review

## D02

Verdict: not accepted yet.

The five extracted lock tutorials replay and the three focused model tests
pass. They cover competition, expiry overlap, fencing-token stale writes,
ownership-aware release, and unavailable-service safety. However, the v3
printed checkpoint only demonstrates an old release being ignored and directly
extends a lease dictionary's expiry. It does not attempt a stale-owner renew
or verify that the real `LockService.renew` rejects it; the model has that
check but no focused test exercises renew ownership. Add stale and current
renew assertions to the checkpoint/tests before acceptance.

## C01

Verdict: pass against the original roadmap scope.

The complete fences and model cover unknown outcomes after timeout, the Two
Generals lost-final-ack boundary, explicit reject-versus-serve-old CAP
partition policies, quorum intersection and versioned reads, and the explicit
non-linearizability boundary. The v3 tutorial states that intersection alone
does not provide linearizability.

Independent verification:

```text
uv run pytest tests/consensus/cap_quorum -q
9 passed in 0.21s
uv run pytest tests/coordination/locks -q
3 passed in 0.02s
uv run python tests/coordination/locks/replay_d02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
```

No reviewer source or tutorial edits were made.
