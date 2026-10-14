# C02 v1: timeout starts a campaign

Scenario: v0 showed timeout-only split brain. Here `a` wins term 1, `b` loses in the same term, then isolated `a` stops sending heartbeats and `b` wins term 2.

Pressure/change: retain explicit logical time and ordered vote messages, but count a majority before setting `leader`.

Checkpoint: all initial votes go to `a`; `b` has not timed out at time 4 but has at time 6. Output is `term1_winner='a'`, `term2_winner='b'`; both old and new leaders can still retain leader beliefs.

Limit/next: a granted vote is only durable local state; a resource can still be written by an old leader. v2 focuses on restart preserving a granted vote.

Replay: `uv run python tests/consensus/leader_election/replay_c02.py --version 1`.

**Naive:** promote on the timeout used in v0. **Break:** timeout cannot prevent competing same-term winners. **Change:** count majority votes and reject a second candidate in the same term. **Check:** `a` wins term 1, `b` loses term 1 and wins term 2 after isolation. **Freeze:** complete model/experiment fences with `run(1)`. **Limit/Still-lacks:** old resource writes are not fenced. **Next:** v2 verifies granted votes across process restart.
