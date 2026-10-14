# S04 v0-v2 revised independent review

## Verdict

pass for original roadmap v0-v2 scope. v3 remains pending S05 v1 and is not
accepted here.

## Resolved findings

The repeated generic prose was replaced by concrete progression: observable
negative file reads, bit-array membership with stable hashing, then a numeric
three-parameter sweep. Bit indexing, masks, double-hash correlation, payload
memory accounting, and formula assumptions are explained. Markdown fences are
properly paired. v1 forces a false positive without claiming it proves true
membership. v2 does not conceal the missing SSTable integration prerequisite.

The sweep computes actual false positives from disjoint present/absent key
sets for all eight combinations of m=512/2048, k=1/4, n=40/160, each with
10000 probes. It also checks no false negatives and prints actual bytes and
theoretical/measured rates. Source measure.py matches the printed checkpoint;
no precomputed rates substitute for the experiment.

## Independent verification

Inspected the replay harness: each version's complete printed files are
materialized into a fresh temporary directory, then its printed checks run
using that directory as PYTHONPATH. Executed:

```text
uv run python tests/storage/bloom/replay_s04.py
uv run pytest tests/storage/bloom -q
7 passed in 0.24s
```

All three versions replayed. Selected observed rows:

```text
bits hashes inserted bytes false/probes theory measured
512 1 40 64 749/10000 0.075151 0.074900
512 4 160 64 2534/10000 0.259158 0.253400
2048 4 40 256 3/10000 0.000032 0.000300
2048 4 160 256 61/10000 0.005188 0.006100
```

The low-probability discrepancy is visible rather than hidden; the guide
explains finite samples and correlated double hashing and does not demand
equality with the approximation.

## Exact hashes

```text
v0 2785571ff4cbeaabefcccef99cd5c9c7661f24c225b716d02dc79be82f312bf6
v1 d51fd33e8bcc355fce316026d2564a3222c7e4da6ef730cbe62091a978a8ec95
v2 07b5573f9a38124af7074c1a937fc23704ab773f09219ab315579af221bf6966
```

No source/tutorial modifications performed. Earlier v3 integration findings
remain open until the actual S05 v1 dependency and filtered lookup are reviewed.
