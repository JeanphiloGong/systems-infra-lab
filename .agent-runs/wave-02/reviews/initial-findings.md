# Wave 02 initial findings

## Blocking findings

- S02 v2/v3/v4 printed `tree.py`: `_leaf` uses bisect_left although separators
  are right-child minima. Printed v2 code with capacity 3 and inserted keys
  10,20,30,40 returns None for get(30). Use right routing for separator equality
  and verify the printed checkpoint independently.
- The same printed code passes the root to `_insert_parent` when splitting a
  deep leaf. Continuing inserts 50..290 raises `ValueError: list.index(x): x
  not in list`. Find the direct parent and preserve split propagation.
- v2/v3/v4 contain the same full algorithm, including recursive internal splits
  and leaf-chain scans already in v2. They do not form the declared learning
  progression. Provide distinct complete checkpoints and targeted reader-visible
  checks for leaf split, recursive split, and scan increments.
- T03 v0 omits the schema.sql setup, later tells readers to run an uncreated
  check_t03.py, and prints a module with import-time database work while the
  real implementation uses a main guard. Supply exact files/setup and one
  coherent complete checkpoint.
- T03 v1 prints only a function and refers to an unprinted complete module/CLI.
  Supply the exact caller change and assembled checkpoint.

## Required revisions

- S02 v4 says closed interval while code excludes end. Choose and explain one
  range contract and test its boundaries.
- S02 validate claims structural verification but does not check equal leaf
  depth or capacities. Add assertions corresponding to the claimed invariants.
- S02 v0's TypeVar is not class-bound; either bind it with Generic or choose
  a concrete value type. Text says integer values while examples use strings.
- S02 v1 abruptly changes parallel arrays to pairs without explaining why.
  Explain representation, O(n) key-list rebuilding, full-page overwrite-before-
  rejection, and test no mutation after overflow.
- T03 v1's zero-row UPDATE can mean conflict, missing row, or failed quantity
  predicate. Qualify the conflict claim to the initialized experiment.

## Verification so far

S02 v0/v1 printed checks ran successfully in temporary directories; four
focused implementation tests passed. This is not tutorial acceptance until
the small stated revisions are resolved. S02 v2 reproduction used code
extracted directly from its printed fence, not current source.

Verdict: no Wave 02 version accepted yet. Authors received exact findings and
must request rereview after revisions.
