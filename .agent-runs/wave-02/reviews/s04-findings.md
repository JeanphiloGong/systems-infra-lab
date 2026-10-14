# S04 review against original roadmap

## Findings

- [block] `labs/storage/bloom/table.py:7`: caller-supplied `keys` can disagree
  with the actual file, producing false negatives. Reproduced file
  `a\t1\nb\t2\n` with `ImmutableTable(path, ["a"])`: query("b") returned
  `(None, 0)` despite an existing value. Derive membership from the same
  authoritative SSTable contents, or validate the complete supplied key set
  before allowing filtered reads. Add a disagreement regression check.
- [block] `tutorials/01-storage-engines/04-bloom-filter/v3/tutorial.md`:
  the original roadmap explicitly requires S05 v1 and integration with its
  immutable SSTable. No S05 checkpoint exists; this version instead defines
  an unrelated TSV reader. Complete the prerequisite and integrate the
  filter with its actual query path, retaining baseline-result comparisons.
- [revise] `v2/tutorial.md:31`: a single configuration (4096 bits, 5 hashes,
  100 inserted keys) and two loose `<0.1` assertions do not satisfy the
  roadmap's capacity/hash-count/insert-count sweep. Print numeric theoretical
  and measured false-positive rates, sample counts, and actual bit-array bytes
  for each controlled configuration. Explain the theory's approximation and
  sufficient absent-key sampling; do not demand deterministic equality.
- [revise] `v3/tutorial.md` and `tests/storage/bloom/test_s04_table.py` do not
  force a false positive. A one-bit filter with inserted keys deterministically
  returns “possibly present” for an absent key; query must then read the true
  table and return None. Reviewer confirmed current code returns `(None,1)` in
  this case, but the tutorial's stated key safety branch lacks acceptance
  evidence. Include a printed check through the real integrated SSTable.
- [revise] `v3/plan.md:3` says the filter cannot prove absence. This reverses
  the Bloom contract: a correctly constructed negative proves absence within
  the covered immutable set; a positive cannot prove presence. Fix the plans
  consistently and explain construction/immutability prerequisites.
- [revise] v1/v2/v3 tutorials introduce bit addressing, double hashing, sizing,
  and filtered-file construction as terse final code with the same generic
  introductory paragraph. Explain the concrete preceding failure and the new
  mechanism, especially `position//8`, masks, modulo positions, and why possible
  membership still requires a true lookup. Their current plans also lack
  version-specific verification/dependencies promised by the tutorial skill.
- [revise] Extra standalone triple-backtick fences follow Python fences in
  v1, v2, and v3 (for example v2 line 26), breaking normal Markdown fence
  pairing. The regex replay tolerates these malformed fences; fix rendering
  and verify the document's actual code-block structure.

## Evidence boundary

`uv run python tests/storage/bloom/replay_s04.py` printed success for all four
versions. This verifies only the small supplied checks; it does not establish
the original sweep/integration/failure requirements. Reviewer independently
reproduced the false-negative key mismatch and forced false-positive fallback.

No S04 acceptance is granted by this review. No source/tutorial files changed.
