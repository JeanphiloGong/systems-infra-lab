# C01: CAP, quorum, and indistinguishable failure

This tutorial models a two-site partition without implementing Raft or automatic leader election.

- v0 shows that a timeout cannot tell whether a remote operation failed or completed.
- v1 uses a lost acknowledgment trace to explain the Two Generals boundary.
- v2 makes the CAP choice explicit: reject requests for linearizable safety or serve an old read for availability.
- v3 computes read/write quorum intersections and demonstrates why arithmetic alone does not prove linearizability.

The model names safety and liveness separately. A partition is a communication failure, not proof that the remote node is dead.

