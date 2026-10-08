# QORE — CIBO Trader Lab: 9–11-minute runtime incident and multi-workflow repair

**Date:** 2026-10-08. **Repository:** `mezas3238-hue/qore-core`.
**Staging:** `agent/cibo-trader-lab-ultrafast-widefix-20261008-001`; target `agent/cibo-causal-expectation-leakage-fix-001`.

## Root cause verified from real GitHub Actions jobs

The 11:18 / 10:58-minute executions were **not runner queue delays**.
- MEDIUM context-stop, run 37757418981: input recovery 30s, replay computation **637s**.
- MEDIUM balanced-regime, run 37757692092: input recovery 14s, replay computation **637s**.
- Legacy scripts launched 8–12 full Python replay processes in parallel on a GitHub Actions runner; every child reparsed six complete M5 histories and recomputed expensive lifecycle maps.
- Earlier Ultra Fast implementation accelerated **two named workflows only**. Other CIBO suites never received those changes.
- Found a secondary performance bug: exact-result-cache invalidation hashed every Python script in `scripts/`, even unrelated audit scripts. Fixed to hash the sovereign `src/qore/**/*.py` tree plus the two active CIBO replay entrypoints, while retaining dataset/CLI/manifest SHA256 identity.

## Measured same-results replacements

All values below are **real job wall time** (not just hot replay), cold on a new staging branch. Every comparison reuses unchanged trading parameters; strict-Pareto result rows match the original run exactly, including capital, DD, loss and PF fields.

| Workflow | Legacy job | Old | New job | New | Cases | Exact result comparison |
| --- | --- | ---: | --- | ---: | ---: | --- |
| 37655 MEDIUM Context Stop | 37757418981 | 678s | 37759319715 | 114s | 11 | 0/275 field differences |
| 37655 MEDIUM Balanced Regime | 37757692092 | 658s | 37759326360 | 90s | 11 | 0/275 |
| 37655 MEDIUM Extreme Cluster | 37757541882 | 423s | 37759331934 | 88s | 10 | 0/250 |
| 37772 ATTACK Context Stop | 37755900609 | 377s | 37759337978 | 69s | 8 | 0/200 |
| 37655 ATTACK 2020 Context2 | 37757846297 | 374s | 37759342981 | 99s | 9 | 0/225 |
| 37810 CRS15 Pressure Depth | 37715862231 | 430s | 37759527853 | 53s | 12 | 0/300 |
| 37990 MEDIUM Stop Fine | 37715231328 | 427s | 37759533205 | 51s | 12 | 0/300 |
| 37772 Pressure Cliff Micro | 37716531543 | 417s | 37759539517 | 43s | 11 | 0/275 |
| 37990 Dual Pressure 2021 | 37714812215 | 415s | 37759549674 | 50s | 12 | 0/300 |
| 37772 Direct Cap Taper | 37738653304 | 382s | 37759558306 | 49s | 11 | 0/275 |
| 37772 H1 Balanced 522 | 37738699432 | 381s | 37759571317 | 51s | 11 | 0/275 |

**Total: 11 newly migrated workflows; 118/118 test cases, 25 fields per case, 0 differences.**
The previously repaired two workflows remain intact.

## Implementation
Each migrated workflow now:
1. Runs the unchanged CIBO replay CLI arguments through `scripts/cibo_trader_lab_batch_runner.py` with 4 bounded Linux fork workers, instead of 8–12 full interpreters.
2. Restores one SHA256-fingerprinted, immutable, causally selected prepared-M5 dataset; cold runs build from independently checked sources.
3. SHA256-verifies the three input archives on restore as well as on fresh download.
4. Reuses an exact-result cache only for *the same replay* (same data, CLI arguments, source, manifest, result path). New configurations always recompute.
5. Fails the workflow at 3 minutes, publishing speed regressions rather than letting 9–11-minute jobs appear successful.
6. Keeps the original 3,368 decision and sovereign-breach assertions in the rank stage.

## Whole-repository audit
`scripts/cibo_trader_lab_runtime_audit.py` and
`.github/workflows/cibo-trader-lab-runtime-audit.yml` perform a reproducible inventory.
Latest audit run **37759818652**: 252 `cibo-trader-lab-*.yml` files, **92 remaining legacy full-CLI fanout** workflows, 13 already using batch, 147 different patterns. The audit checks 11 newly migrated suites for regression and blocks any increase above 92 legacy fanout workflows.

**Critical: This does NOT certify the remaining 92 workflows as fast.**
The remaining legacy jobs need migration under a separate controlled staged sequence and strict old/new replay-result parity. The audit artifact lists their exact names.

## Required science and safety
- No sovereign economic algorithm, sizing, leverage, stop, compounding or DD thresholds was changed by this speed work.
- Historical reused holdout results remain hypothesis generation. Cached duplicate results are not fresh OOS evidence.
- Fresh 3-year holdout required after scientific work; do not use speed optimizations to infer a 20–25% DD.
- No claim that all 252 CIBO workflow types or all 434 repository workflows are accelerated.
