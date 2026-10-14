# Q02 and Q03 acceptance correction

Both modules are reopened. This supersedes q02-v0-v3-final.md and
q03-v0-v3-final.md. Earlier green Python-model replays did not establish the
original PostgreSQL requirements and should not have been accepted as complete.

Q02 requires actual EXPLAIN/read counts, selectivity-dependent plans,
composite filtering/range/order comparisons, and PostgreSQL index-only heap
fetches after UPDATE and VACUUM. Direct dictionary operations and hand-set
visibility flags do not provide that evidence.

Q03 requires stale/fresh statistics with ANALYZE and actual plan changes,
correlated data and appropriate statistics, and observed join/sort resource
behavior. Assigned constants cannot count as observed rows or I/O. The prior
chunked-sort example also never wrote spill files or merged sorted runs, so
its calculated spill bytes were not observed external-sort I/O.

Root is arranging real PostgreSQL experiments. Acceptance must be based on
those experiments and printed tutorial replay, preserving original scope.
