# C02 v4: belief, permission, and recovery

Scenario: partitioned or restarted nodes retain an old belief while the quorum elects a newer owner. Old writes must remain forbidden until the node learns the newer term.

Pressure/change: model partition and restart separately from election, persist the epoch, and require current owner/term for resource writes and heartbeats.

Checkpoint: replay reports partition and restart cases with `old_belief_before_heal=True` only where expected, and every `old_write_allowed` is false; healing updates the stale node before permission returns.

Limit: fixed membership, local logical clock, and no linearizable read protocol. Later distributed-state lessons cover broader lease/replication failure recovery.

Replay: `uv run python tests/consensus/leader_election/replay_c02.py --version 4`.

**Naive:** equate local belief with permission after partition. **Break:** stale nodes attempt writes before healing. **Change:** persist epoch and require current owner/term for writes and heartbeats. **Check:** every `old_write_allowed` is false and healing updates term. **Freeze:** complete model/experiment fences. **Limit/Still-lacks:** no linearizable reads or dynamic membership. **Next:** distributed-state recovery.
