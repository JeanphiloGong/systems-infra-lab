# R02: consistency models and read contracts

This tutorial models profile updates replicated from one writer to a lagging read copy. It names the read contract each version can actually test:

- v0 eventual consistency and stale reads.
- v1 session read-your-writes.
- v2 linearizable reads in a fixed single-writer, no-failover model.
- v3 read repair for a key observed on a lagging replica.
- v4 a comparison of eventual, session, snapshot, and linearizable reads, including a partition failure.

The model is local and deterministic. It does not claim a formal proof or implement a distributed consensus protocol.

