# P01 author evidence

Scope: P01 v0-v3, no roadmap reduction. Python 3.14.0, uv locked environment.
Each version's behavior tests were written first and collection failed for the missing module;
the implementation then made the corresponding tests pass. No production adapters introduced.

## Checks

- v0: `uv run --locked pytest tests/partitioning/routing/test_p01_single.py -q`: 2 passed.
- v1: `uv run --locked pytest tests/partitioning/routing/test_p01_hashing.py -q`: 5 passed.
- v2: `uv run --locked pytest tests/partitioning/routing/test_p01_ranges.py -q`: 8 passed.
- v3 integration: `uv run --locked pytest tests/partitioning/routing/ -q`: 23 passed.
- `uv run --locked python .agent-runs/wave-01/replay_p01.py`: all four printed checkpoints
  rebuilt in separate temporary directories; all printed shell checks passed.

Replay outputs: v1 moved 756/1000 keys with modulo 3→4; v3 ring moved 2749/10000,
modulo moved 7485/10000. Virtual point counts 1 yielded a=4373,b=4566,c=1061;
64 yielded a=3239,b=3428,c=3333. These are deterministic fixture observations, not load guarantees.

## Implementation boundaries

`stable_hash` is a permanent teaching helper for reproducible routing. RangeMap and HashRing
are permanent direct representations of their respective configurations; no common interface,
adapter, persistent database or automatic migration was introduced. Temporary replay directories
are automatically removed. No existing source was removed or refactored.

## Independent review

v0-v1 independently passed in `reviews/s03-v0-p01-v0-v1.md`. v2-v3 independently passed
in `reviews/p01-v2-v3.md`. All four versions accepted for routing-only scope.
