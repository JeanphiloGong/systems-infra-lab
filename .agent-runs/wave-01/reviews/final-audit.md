# Wave 01 final audit

## Accepted versions

The following 24 tutorial versions were independently reviewed and accepted:

- S01 pages/locality: v0-v4 (5)
- S03 WAL/recovery: v0-v5 (6)
- T01 isolation: v0-v4 (5)
- T02 MVCC: v0-v3 (4)
- P01 routing: v0-v3 (4)

This is acceptance of these 24 checkpoints only; it is not completion of the
full 196-checkpoint course.

## Final verification

S03 v5 was rechecked after the `tail_repaired` coverage fix. The repository
replay produced all six version outputs and the 20-case crash matrix,
including a separate real child-process tail repair crash with an acknowledged
prior transaction, repeated fresh recovery, and subsequent append. Final
command: `uv run pytest tests/storage/wal -q` -> 34 passed.

T02 v1-v3 were rechecked after replacing whole intermediate experiment regions
and adding the explicit guard initialization. Reviewer-owned replay ran the
serial, write-skew, conflict, and retry patches against isolated PostgreSQL;
`uv run pytest tests/transactions/mvcc -q` -> 15 passed.

P01 v0-v3: printed checkpoints replayed in temporary directories and 23
routing tests passed. S01 v0-v4: independent checkpoint replay and 18 tests
passed. T01 v0-v4: independent PostgreSQL replay and 26 current tests passed
(25 at the earlier fix audit; the later connection-refusal contract test is
included in the current count).

## Final document hashes

S03 v0-v5:

```text
38f0fc178698fff115753643a78c8906aa8fef2efa642981b00166dfcf454f53
14936440be83bc8c01284743d7530d337190a7eedadc86e53a2d723ef31f254f
2cdb85b349f9c74f395d0c8e664558778cfb6fcc9b8d4f244423aa39b1bdb34e
ed9816e31dbb1d3cdb3f1708388980dc65d15b9613d470e7fab14f03bc88f3f2
7d29ab4795d1b4df4a719bf986584a2b42d3e910ba75c2e2c05d4a9aa2fd9827
633fcec969af876c79524be391961393365819667bec422cbd0b1b967ccc6e21
```

T02 v0-v3:

```text
ad04e18c6fed53b75300eff8e5b65db64222cabf177ab0dd04d57f97626ac1ab
81179a939830ce5191fc1680a7e51fe444d79ad78171a580686663dbd02aafaa
76463d58a2696f5ac092fa41ddbfaa3fb09ecce7267f21c1997e29546e36e99a
e826aaf6eb8a03b769ea1e57ce8c6e85c810c4c3acc92fe61b1cc538f2b2b512
```

Previously accepted S01, T01, and P01 hashes were unchanged at this final
audit. No tutorial source was edited by the reviewer.

## Verdict

pass for all 24 listed versions. Remaining course modules and future versions
require the same author -> independent replay -> findings/fix -> recheck loop.
