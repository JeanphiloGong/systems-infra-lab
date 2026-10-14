# Wave-20 independent live review: C03 v8

## Verification

Used the existing executable at `/tmp/etcd-v3.5.17-linux-amd64/etcd`; no
download or installation was performed.

```text
$ ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd \\
  uv run python tests/consensus/raft/replay_c03.py --version 8
v8 replay ok
etcd: engine=etcd-3.5.17, processes=3, recovered_value=after,
      minority_write_rejected=true

$ ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd \\
  uv run pytest tests/consensus/raft -q
14 passed in 3.55s
```

The v8 replay compared its three source fences to the repository lab sources,
ran model regressions for versions 1, 3, 4, 5, 6, and 7, then started three
local etcd members. It wrote `before`, killed the elected leader, wrote and
read `after` through the surviving majority, restarted the killed member and
recovered `after`, and rejected a write after stopping the two-member
majority. The test suite independently covers the earlier election,
durability, conflict, queue-fault, and snapshot assertions.

The probe's cleanup terminated/reaped members and removed its temporary data;
no matching etcd processes remained afterward. This evidence covers a local
three-process 3.5.17 experiment only; it does not establish independent-host
failure, dynamic membership, or production operations.

## Verdict

**PASS.** C03 v8's live acceptance criteria are met. No implementation,
tutorial, plan, index, or progress file was changed.
