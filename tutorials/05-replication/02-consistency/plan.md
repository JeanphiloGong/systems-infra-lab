# R02 tutorial plan

Scenario: a user changes a profile and refreshes it through a replica. Every version states an invariant and a failure boundary.

1. v0: asynchronous apply exposes an old read; stopping writes is the condition for eventual convergence.
2. v1: a session carries its latest write version and reads from the leader when the replica is behind.
3. v2: a fixed single writer serves reads from current state and records a checkable history.
4. v3: reading a stale key repairs that replica to the leader's ordered version; unread keys remain untouched.
5. v4: compare eventual, session, snapshot, and linearizable contracts; a partition makes linearizable reads unavailable.

The replay test extracts exactly one complete source fence per version and runs it in an isolated subprocess.

