# C03 v3-v8 independent review: REVISE

Original authority: `docs/roadmap.md:416-433`. Green replay does not establish the requested behavior. Actually ran pytest: **6 passed in 0.37s**, and standalone replay printed `C03 tutorial v0-v8 replay ok`. The advanced replay only requires a nonempty stdout string; it neither connects these snippets to the actual Raft model nor validates their claimed semantics.

## Blocking findings

1. **v3 tutorial does not implement majority commit.** Its entire experiment appends two local entries then assigns `commit=2`; no followers, acknowledgments, current-term restriction, or old-term counterexample exist. Worktree `Cluster.replicate` is also unsafe: it counts caller-supplied arbitrary names and commits the leader before attempting follower append, ignoring their result. Actual independent reproduction with acknowledgments `{'unknown1','unknown2'}` committed index1 while logs remained `[1,0,0]`. Derive acknowledgments from actual successful follower replication, validate membership, and verify the current-term commit rule plus indirect commitment of preceding old-term entries.

2. **v4 checks an isolated tuple comparison rather than election safety.** The printed helper is disconnected from persistent request_vote and candidate election. There is no multi-node trace showing a stale candidate denied votes and unable to replace a valid leader containing committed history. Wire freshness into actual voting and exercise both stale and eligible candidates under the same persisted model. Root-level term/vote checks must remain intact.

3. **v5 has no crash injection or restart.** The printed code writes and reads one JSON file in the same process, then prints `restart_recovered=True`. It exercises no log, state-machine application or pre/post-persistence crash boundary. v1's single post-vote process exit does not fulfill v5's explicit boundary set. Add real child exits at the declared boundaries and fresh-process checks for recovered term/vote/log/commit/application consistency.

4. **v6 has no message fault histories.** It computes majority cardinality from a set. There are no dropped, duplicated, reordered or partitioned messages, no commit history comparison, and no restored-majority progress. Add an actual deterministic message schedule over the same nodes and compare committed/applied histories through failure and healing.

5. **v7 neither installs nor safely compacts a snapshot.** The printed snippet only returns a dictionary. Worktree `snapshot()` additionally saves the current full state even for an earlier prefix, subtracts commit/application indices, and keeps no persistent absolute base index. Independent reproduction: committing entries1 (`x=1`) and2 (`x=2`), then snapshotting index1 stored `x=2`; appending afterward produced log indices `[2,2]`. `install_snapshot()` discards last-included term/index entirely. Preserve absolute snapshot metadata and correct prefix state; test installation, restart, suffix continuation and subsequent AppendEntries against the snapshot boundary.

6. **v8 is explicitly unfinished and fabricates acceptance.** Prose admits real multi-process demonstration and full fault replay are absent, while the code sets all five check flags to True and prints `faults_replayed`. Remove this completion claim until an actual combined fault suite and real multi-process demonstration execute. Documentation of a limitation cannot replace a required original-roadmap deliverable.

## Continuity and earlier verdict correction

The v3-v8 one-file snippets do not grow the v0-v2 Node model or import complete dependencies. They must become executable checkpoints of one evolving implementation, with assertions that fail under the relevant safety regressions.

On rereading original v1, the prior `c03-v0-v2-final.md` verdict was too broad: roadmap v1 explicitly includes election timers and simultaneous candidacy traces, but only persistent voting/restart is implemented. Reopen that v1 portion too; retain the observed vote-restart evidence without claiming full original v1 completion. The earlier review also claimed a committed-overwrite test although no dedicated test exists; the guard exists in source, which is narrower evidence.

Review artifacts only; no implementation abstraction or source cleanup added.
