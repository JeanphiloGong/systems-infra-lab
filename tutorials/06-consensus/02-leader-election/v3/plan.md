# C02 v3: resource fencing follows term and owner

Scenario: an old leader pauses after election while a successor wins a newer term. A stale write must be rejected even if the old node still believes it is leader.

Pressure/change: add `Resource.write(owner, term, version, value)` checks for current term, owner, and deadline; campaign/recovery updates the resource epoch.

Checkpoint: old-term write is rejected, the successor write succeeds, and replay reports `old_write_rejected=True` with `value='successor'`.

Limit/next: this is a local lease/resource model, not a clock-synchronized production lock. v4 separates node belief, permission, and recovery after partition/restart.

Replay: `uv run python tests/consensus/leader_election/replay_c02.py --version 3`.

**Naive:** let a paused old leader write on belief alone. **Break:** newer term owns the resource while old write is still attempted. **Change:** require current owner, term, version, and deadline. **Check:** old write rejected and successor value observed. **Freeze:** complete model/experiment fences. **Limit/Still-lacks:** local logical lease only. **Next:** v4 models partition/restart recovery.
