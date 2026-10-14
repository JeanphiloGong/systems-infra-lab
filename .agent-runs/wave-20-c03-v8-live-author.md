# C03 v8 live execution evidence

The earlier missing-binary limitation is resolved for this run. Reviewed the
v8 tutorial, `etcd_demo.py`, and `.agent-runs/wave-04-C03-repair.md`, then
found the existing historical binary under `/tmp`. No download or global
installation was needed; the existing executable was left intact.

```text
$ /tmp/etcd-v3.5.17-linux-amd64/etcd --version
etcd Version: 3.5.17
Git SHA: 507c0de
Go Version: go1.22.9
Go OS/Arch: linux/amd64

$ ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd uv run python tests/consensus/raft/replay_c03.py --version 8
v8 replay ok
etcd: {engine: etcd-3.5.17, processes: 3, killed_leader: 0,
       recovered_value: after, minority_write_rejected: true}

$ uv run pytest tests/consensus/raft -q
14 passed in 3.05s
```

The replay first compared all three v8 source fences to root lab sources,
then extracted and executed them in an isolated temporary directory. Its
model regressions also passed: split-election recovery, current-term commit
boundary, stale-candidate rejection, all 12 publication crash cases, queued
network faults, and snapshot recovery.

The real process experiment started three local etcd members, wrote `before`,
killed the elected leader, wrote `after` through the surviving majority,
restarted the killed member and read `after`, then stopped the two survivors
and observed no successful acknowledgment for a minority write. A timed-out
request does not establish that its mutation can never commit later.

Cleanup: the probe's finally block terminated/reaped its members, closed logs,
and removed temporary data directories. A post-run `pgrep` for this binary's
`--name n0/n1/n2` command lines returned no matches. The temporary filesystem
search was stopped after finding the binary. No user service was stopped.

Only this evidence file was added. No implementation fix or new abstraction
was necessary; no tutorial, plan, progress, or index was modified. This is a
local three-process experiment, not evidence about independent hosts, arbitrary
partitions, dynamic membership, or production operations. The reused binary's
version was checked; a release checksum was not revalidated in this run.
