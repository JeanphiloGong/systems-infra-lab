# C01 build evidence

C01 uses deterministic partition models under `labs/consensus/cap_quorum/`:

- v0 `v0.py`: delayed or dropped messages leave a remote operation outcome unknown after timeout.
- v1 `v1.py`: a lost final acknowledgment leaves both parties uncertain, illustrating the Two Generals boundary.
- v2 `v2.py`: explicit partition policy choices between rejecting linearizable reads and serving an old value for availability.
- v3 `v3.py`: read/write quorum set intersection and a versioned quorum-read helper; intersection arithmetic is kept separate from a linearizability claim.

Each tutorial version under `tutorials/06-consensus/01-cap-quorum/` contains one complete source fence marked with its exact target path. Replay extracts and executes all four fences in isolated subprocesses.

Verification:

```text
uv run python -m compileall -q labs/consensus/cap_quorum
uv run python -m pytest tests/consensus/cap_quorum -q
9 passed
```

The model does not implement leader election, Raft, or formal CAP/consensus proofs. A quorum intersection is a visibility condition, not by itself a guarantee of linearizability. No commits were made; independent review is required.

