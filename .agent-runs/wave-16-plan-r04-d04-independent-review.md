# R04/D04 Plan Batch Independent Review: PASS

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## D04 Saga

The complete D04 suite passed:

```text
$ uv run pytest tests/coordination/saga -q
..........                                                               [100%]
10 passed in 0.29s
```

The ten tests include exact v0-v4 tutorial fence replay and behavior checks
for partial effects, durable resume, reverse compensation, manual
intervention after retry exhaustion, and concurrent idempotent order effects.
An independent fence/source comparison found every v0-v4 fence equal to its
`labs/coordination/saga/vN.py` source.

## R04 PostgreSQL replication

The dedicated three-service stack was started from clean volumes with
`infra/r04.compose.yaml`. The first immediate test run encountered a startup
race: v0 connected while the standby was still entering recovery, and v2
timed out before physical DDL replay. Standby logs then showed:

```text
entering standby mode
consistent recovery state reached
database system is ready to accept read-only connections
started streaming WAL from primary
```

After the standby reached readiness, the complete live suite passed:

```text
$ R04_DATABASE_URL='postgresql://r04:r04_local_only@127.0.0.1:55440/r04' \
  uv run pytest tests/replication/postgres -q
.....                                                                    [100%]
5 passed in 3.09s
```

This covers v0 physical streaming/read-only standby, v1 selective logical
publication, v2 DDL/sequence/replica-identity boundaries, and v3 paused
logical-consumer WAL retention and recovery. The tests compare every tutorial
checkpoint fence with its referenced source before running the subprocess;
an independent comparison found all R04 v0-v3 Python and support fences
exactly matched their lab files.

The initial failure was a service-readiness race rather than a stable
behavior failure. The clean-volume rerun established the intended topology;
the dedicated R04 stack was removed afterward with
`docker compose -f infra/r04.compose.yaml down -v`.

## Decision

**PASS for R04 and D04.** The plans are concrete and version-specific, the
Saga and PostgreSQL checkpoints have exact tutorial/source fidelity, and the
live behavior suites pass once the standby is ready. No implementation,
tutorial, plan, progress, or index files were changed; only this review
artifact was added. No abstraction or cleanup was introduced beyond removal
of the dedicated R04 test stack.
