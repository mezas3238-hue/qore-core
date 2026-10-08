# CIBO — 37082 MEDIUM Trough Context2 16-minute workflow repair
Date: 2026-10-08

## Evidence: the screenshot corresponds to run 37759321394
- Workflow: `.github/workflows/cibo-trader-lab-carrier37082-medium-trough-context2-ridge.yml`.
- Research branch: `agent/cibo-causal-expectation-leakage-fix-001`.
- Original job 113251594215, **09:49:34Z–10:05:57Z = 983 seconds = 16:23**.
- Actual Python case execution step: **09:49:51Z–10:05:53Z = 962 seconds = 16:02**.
- Source recovery: 13 seconds. Slowdown is NOT runner queue.
- Legacy workflow spawned **13 distinct Python interpreters simultaneously** with complete `RAW_M5` parsing on the same runner; 13 overlapping memory/CPU-heavy lifecycles.

## Fix implemented without changing economic or lifecycle logic
1. Replace 13 `run_case ... &` children and `wait` with 13 exact CLI JSONL argument vectors plus one `scripts/cibo_trader_lab_batch_runner.py` call.
2. Four bounded Linux fork workers share one immutable, per-trade M5 window preload via copy-on-write; unchanged `cibo_trader_lab_three_mode_ceiling.main()` invoked for each case.
3. Reuse authenticated SHA256 historical/source/control artifact inputs and fingerprinted prepared six-symbol M5 cache. Exact case memoization only for identical source code, CLI flags, output name and immutable data.
4. Preserve the existing 3368 entry count, zero sovereign breach and Pareto/DD rankings.
5. Give the workflow a 3-minute timeout (fail-closed against future unexplained slowdowns).
6. Add the workflow to `scripts/cibo_trader_lab_runtime_audit.py` MIGRATED contracts to prevent a revert to legacy full Python fanout.
7. Research reused-holdout only; this has no bearing on fresh 3-year holdout certification.

## Strict A/B results
| Metric | Original (37759321394) | Cold optimized (37761318560) | Warm exact repeat (37761606762) |
| --- | ---: | ---: | ---: |
| GitHub Actions job wall time | 983s | **123s** | **21s** |
| Cases | 13 | 13 | 13 |
| Exact comparable fields per case | 25 | 25 | 25 |
| Differing field values against original | 0 | **0** | **0** |
| New completed full replays | 13 | 13 | 0 (all 13 cached) |
| Sealed exact case result hits | 0 | 0 | **13/13** |
| Pareto PASS variants | 0 | 0 | 0 |
| DD ≤25% PASS variants | 0 | 0 | 0 |
| Run status | SUCCESS | SUCCESS | SUCCESS |

**Novel 13-case suite runtime:** 123 seconds on a cold new branch, which is improved ~8x but remains above a 60-second target. **Identical repetition** was 21 seconds, but this must never be misrepresented as new OOS evidence or new strategy discoveries.

## Remaining open systemic work
This change migrates **one named workflow**. The canonical audit still reported ~95 other legacy oversubscribed workflows on 2026-10-08, changing as concurrent architects publish new suites. Every new research sweep must use the prepared runner rather than introducing another Python-per-case fanout; existing legacy suites need controlled migration with exact 25-field A/B parity before claiming completion.
