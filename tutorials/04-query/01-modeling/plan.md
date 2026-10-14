# Q01 plan

One order scenario evolves from duplicated customer/product columns to normalized entities and an explicitly maintained read model. The key invariant is that historical purchase price is immutable while current descriptive names may change. Metrics compare reads, writes, and stale-view risk; they are logical operations, not database benchmarks.
