# R01 v0 two-process repair evidence

Closed the remaining v0 review gap by adding explicit `--writer` and
`--reader` modes to the complete source fence and implementation. The writer
process applies two ordered entries and exits after writing the JSON
checkpoint. A separately launched Python process opens that checkpoint and
prints the recovered position and data. The focused test asserts both process
outputs exactly, so it proves a process boundary rather than a fresh object in
one interpreter.

```text
$ uv run pytest tests/replication/leader_follower/test_r01.py::test_v0_writer_and_receiver_are_separate_processes -q
1 passed
$ uv run pytest tests/replication/leader_follower/test_replay_r01.py -q
6 passed
$ diff -u <(sed -n '/^```python$/,/^```$/p' tutorials/05-replication/01-leader-follower/v0/tutorial.md | sed '1d;$d') labs/replication/leader_follower/v0.py
(no output)
```

The checkpoint remains a small local JSON teaching mechanism; atomic rename,
checksums, and multi-replica recovery are intentionally deferred to later
durability topics. No shared progress/index or R03 files were changed.
