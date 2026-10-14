# C03 v4: log freshness gates election

Scenario: candidate `c` has a shorter log and requests votes while `b` has the committed suffix. Granting `c` would lose committed data.

Pressure/change: compare last log term and index in `request_vote`; only an up-to-date candidate can win, then preserve the committed command through replication.

Checkpoint: stale candidate receives one vote (itself), `b` wins, and every state equals `{'mode': 'committed', 'next': 'kept'}`; output includes `stale_candidate_votes=1`.

Limit/next: no disk crash boundary is exercised. v5 kills processes at each publication boundary.

Freeze artifact: the exact historical fences are retained at `labs/consensus/raft/checkpoints/v4/advanced.py` and `advanced_experiments.py` for parity comparison.

Replay: `uv run python tests/consensus/raft/replay_c03.py --version 4`.

**Naive:** grant a shorter-log candidate a majority. **Break:** committed suffix could be lost. **Change:** compare last term/index in request_vote. **Check:** stale candidate one vote, b wins, committed/next state preserved. **Freeze:** v4 snapshots named above. **Limit/Still-lacks:** no crash publication test. **Next:** v5 filesystem boundaries.
