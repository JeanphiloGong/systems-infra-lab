# C01 tutorial plan

1. v0: delayed and dropped messages leave the operation outcome unknown.
2. v1: a lost final acknowledgment leaves both generals uncertain.
3. v2: a partition policy chooses refusal for linearizable reads or availability with an old value.
4. v3: quorum sets intersect when R + W > N, but stale or concurrent versions still require ordering and protocol rules.

Every version has one complete source fence and a deterministic partition experiment. The module does not claim consensus, election, or formal CAP proof.

