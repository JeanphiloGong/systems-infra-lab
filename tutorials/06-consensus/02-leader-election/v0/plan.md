# C02 v0: silence creates competing leader beliefs

Scenario: three workers contend for one resource while messages are delayed. A node must not self-elect on timeout alone; a term permits one vote per node.

Pressure/check: isolate existing leader `a`, advance the logical clock to 6, and let each timed-out node declare itself leader. Expect `timeout_self_elected=['a','b','c']` and `split_brain=True`.

Change/freeze: freeze the complete `model.py` and `experiments.py` fences, executing only `run(0)`. The change is an observable timeout-only baseline; shared helper code includes later mechanisms, but this version does not exercise them.

Limit/next: fixed three-node membership and no fencing of a paused leader. v1 makes timeout start a campaign but separates candidacy from authority.

Replay: `uv run python tests/consensus/leader_election/replay_c02.py --version 0`.

**Naive:** silence is treated as proof of leadership. **Break:** at logical time 6 all three nodes believe they lead. **Change:** expose this failure through `run(0)` and measured leader beliefs. **Check:** exact three names and `split_brain=True`. **Freeze:** the two complete tutorial fences, invoked with version 0. **Limit/Still-lacks:** this baseline neither elects by quorum nor fences writes. **Next:** v1 requires majority votes.
