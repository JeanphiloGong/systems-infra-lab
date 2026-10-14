# E04 independent review: revise

The four extracted replay tests pass (**4 passed in 0.68s**) and the experiments
cover the requested batch provenance, late correction, ATTACH federation/index
plan, and copied-vs-live source behavior. One source-quality issue blocks the
checkpoint: `labs/dataflows/analytics/v3.py` contains

```python
warehouse.execute("INSERT INTO orders SELECT * FROM main.orders") if False else warehouse.executemany(...)
```

This dead branch is unexplained final logic and is not a meaningful teaching
boundary. Remove it and use one direct, readable copy operation; refresh the v3
tutorial fence and exact extraction test. Re-run all four isolated experiments.

No progress acceptance or commit performed.
