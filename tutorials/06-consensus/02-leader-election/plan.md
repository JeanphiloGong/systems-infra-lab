# C02: Election Plan

The scheduler must protect one shared resource even when an old leader stops receiving messages and later resumes. Fixed three-node membership, sequential deterministic message events, persisted votes, and a resource-owned lease reduce this to a runnable protocol experiment.

1. v0: make heartbeat timeout self-election create three leadership beliefs under partition; assert the counterexample.
2. v1: replace authority-by-timeout with per-node term/vote decisions and a two-of-three quorum; trace delivered votes and distinguish same-term quorum uniqueness from concurrent beliefs across terms.
3. v2: persist votes before replying; terminate a writer process and verify a different process cannot grant a conflicting vote at that term.
4. v3: register only quorum winners with the protected resource; reject writes on owner mismatch, older term, or expired lease without modifying data.
5. v4: compare partition, GC pause, and restarted node; heal the graph, deliver a newer heartbeat, and reject the old owner even when it has learned the current term.

Each tutorial includes full model and experiments modules. The small shared simulator is printed completely in each version; the scenario selected by the command determines the learning increment. Replay reconstructs those modules in an empty directory. It never substitutes current source for a missing fence.

Nine tests check all five scenarios, every candidate ordering, minority failure, old-message rejection, owner checks, and persisted votes. This is not Raft log consensus, a clock synchronization algorithm, or a production coordination service. Resource-service crash recovery and randomized election retries remain out of scope.
