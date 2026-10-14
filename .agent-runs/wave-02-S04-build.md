# S04 revised build evidence

Status: v0-v2 revised; v3 now integrated with real S05 v1 and awaiting independent review. Prior whole-module acceptance claim was withdrawn; revised implementation is not declared approved until independent review.

Independent findings addressed:
- TSV prototype accepted a separate possibly incomplete keys list. Constructor now derives all filter keys from actual file contents; callers/tests updated directly, no compatibility wrapper.
- v2 single loose threshold replaced with eight-combination parameter sweep m=512/2048, k=1/4, n=40/160 and10,000 absent queries. Reports theory, observed counts/rate, false negatives and bit-array payload bytes.
- v0-v2 guides rewritten as pressure-driven explanations with expanded typed source fences, not compressed one-line fillers. v1 checkpoint excludes future formula/sweep; v2 includes complete unchanged filter algorithm plus measurement.
- v3 source prototype was replaced after S05 author froze actual SSTable API. Constructor now scans SSTable.items, True delegates SSTable.get, False skips. Complete S05 v1 source is embedded as a frozen dependency. No caller keys list accepted.
- Strict replay writes only printed files to isolated temp directories; no current-source injection or source-reference substitution.

Tests: `uv run pytest tests/storage/bloom/ -q`:9 passed. Includes separate hash-seed subprocesses, file-derived membership, parameter sweeps, zero/invalid formula inputs, forced bits=1 positive miss returning None with real read, empty-value preservation, reopen and actual Path.open count.
Replay: `uv run python tests/storage/bloom/replay_s04.py`: all4 complete versions pass. v3 baseline302 queries, build1 scan, filtered102 scans. All results same; missing queries actually skipped. Constructor cost separately counted.

v3 RED before integration: all4 SSTable integration tests failed because TSV parser could not read true JSONL. Replaced prototype implementation with actual API; GREEN9 aggregate tests. Full printed SSTable/filter/table dependencies independently replayed without source injection.

Observed v2 output (m,k,n,bytes,FP/10000,theory,observed):
512,1,40,64,749,0.075151,0.074900
512,1,160,64,2753,0.268384,0.275300
512,4,40,64,42,0.005188,0.004200
512,4,160,64,2534,0.259158,0.253400
2048,1,40,256,199,0.019342,0.019900
2048,1,160,256,760,0.075151,0.076000
2048,4,40,256,3,0.000032,0.000300
2048,4,160,256,61,0.005188,0.006100

The dual-hash mapping isn't independent-uniform; formula is an approximation, not assertion. Memory refers to payload, not RSS. File immutable during prototype lifetime. No new adapters or wrappers; cleanup removed placeholder fences and duplicate code-fence delimiters in v0-v2.
