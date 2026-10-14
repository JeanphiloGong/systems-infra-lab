# C02 v2: restart cannot erase a vote

Scenario: node `a` grants `b` a vote in term 7, restarts, then receives another request from `c` for term 7.

Pressure/change: persist `term` and `vote` before returning success; reconstruct volatile `leader` state as false on restart.

Checkpoint: replay must print exactly `{'recovered_term': 7, 'recovered_vote': 'b', 'double_vote_rejected': True}` (JSON equivalent), and the unit test must observe `(7, 'b', False)`.

Limit/next: persistence protects vote identity but does not fence resource writes. v3 adds a term-scoped resource owner.

Replay: `uv run python tests/consensus/leader_election/replay_c02.py --version 2`.

**Naive:** keep a granted vote only in memory. **Break:** restart permits a second same-term vote. **Change:** persist term/vote before acknowledgment and clear volatile leadership. **Check:** exact recovered JSON and `(7, 'b', False)`. **Freeze:** complete model/experiment fences. **Limit/Still-lacks:** no resource fencing. **Next:** v3 adds term-scoped ownership.
