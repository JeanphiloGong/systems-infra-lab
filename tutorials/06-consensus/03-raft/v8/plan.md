# C03 v8: regression suite and real etcd cluster

Scenario: preserve every earlier election, durability, conflict-repair, queue-fault, and snapshot invariant, then verify minority writes and recovery in three etcd processes.

Pressure/change: freeze the complete advanced experiment plus `etcd_demo.py`; run all model versions and an isolated three-process etcd cluster.

Checkpoint: versions 1,3,4,5,6,7 satisfy their prior exact observations; etcd reports engine `etcd-3.5.17`, `processes=3`, recovered value `after`, and minority write rejected.

Limit: fixed educational scenarios, local process orchestration, and no dynamic membership or linearizable-read tutorial. The real etcd section requires the bundled etcd executable/network runtime.

Replay: `uv run python tests/consensus/raft/replay_c03.py --version 8`.

**Naive:** declare the individual demos sufficient without regression or real-process evidence. **Break:** run all prior fault paths and a three-process minority-write scenario. **Change:** one advanced regression experiment plus etcd probe. **Check:** prior version outputs, engine 3.5.17, three processes, recovered `after`, minority rejection. **Freeze:** advanced, advanced_experiments, and etcd_demo fences. **Limit/Still-lacks:** requires ETCD_BINARY and no dynamic membership. **Next:** install etcd and run the real cluster.
