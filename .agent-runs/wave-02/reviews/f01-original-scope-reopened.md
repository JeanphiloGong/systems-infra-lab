# F01 original-scope acceptance correction

Verdict: reopened. This supersedes F01 PASS claims in f01-final.md and
f01-s07-final.md; S07 status is unaffected.

The prior review accepted successful local psycopg-pool examples without
enforcing all original roadmap requirements. In particular:

- F01 v3 requires a transaction-pooling proxy experiment showing multiple
  clients sharing fewer database backend connections and session-state limits.
  The current single-process client-pool example has no proxy and cannot prove
  that behavior. A passing execution does not close this scope gap.
- The module invariant requires both connection and waiting-queue bounds.
  make_pool sets max_size and timeout but leaves psycopg_pool max_waiting at
  its default unlimited setting. Waiting time bounds do not bound the number
  of concurrent waiting callers.
- v0 records one total connect/query/close elapsed time, with no separate
  handshake or connection-count measurement required by its roadmap version.

Explicit application_name persistence documentation is correct but addresses
only the local session-state observation, not the proxy experiment.
