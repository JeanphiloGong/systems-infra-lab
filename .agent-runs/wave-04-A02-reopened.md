# A02 semantic audit: REVISE

Independent root probe against current Store:

1. Commit ten transactions, snapshot(10), recover(): bytes_read=511, exactly
   the full segment bytes. snapshot() does not publish a manifest, so v1 never
   reads its snapshot. Its test checks state only, not bounded recovery work.
2. publish([10]) removes all segments. Corrupt snapshot-000010.json. recover()
   returns ({alice:100,bob:100},0,0), silently losing all committed history.
   Once a manifest exists, absence of any usable recovery base must be an error.
3. publish() never validates referenced snapshots before reclaiming logs;
   publishing a nonexistent position can therefore destroy the only recovery
   path. It also does not reclaim obsolete snapshot generations.

The prior review inaccurately called the manifest checksummed; only snapshots
have checksums. The same final implementation is printed in all three chapters,
and replay executes neither publication nor fallback, so that replay does not
prove v2/v3. Tests also accept negative balances rejected by the frozen v0.

Repair must preserve the v0 transaction/CRC and balance invariants, give v1 a
usable snapshot while retaining old logs, validate durable snapshots before
publication, reject unusable recovery bases, retain the fallback log interval,
and execute each version's actual failure experiments from its printed code.
Include first-log-deletion and generation-rotation crash boundaries, work metrics,
and fresh-process recovery. Do not retain this report's historical pass as current
acceptance. v0 stays accepted; v1-v3 reopen.
