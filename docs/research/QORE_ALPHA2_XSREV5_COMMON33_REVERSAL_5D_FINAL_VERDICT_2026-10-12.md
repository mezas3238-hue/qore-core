# QORE-Alpha 2 — XSREV5 cross-sectional contrarian 5 common-day reversal: one real result and STOP

**Date:** 2026-10-12. **Status:** `XSREV5_GROSS_MINUS_ASSUMED_COST_FAIL`. **NET broker NOT measured; UTC001=FALSE.** No further quintile, horizon, weekday, subuniverse or cost tuning on this previously exposed 2016–2024 dataset.

## Chain of custody and repair chronology

- **Frozen prereg BEFORE this experiment opened any new original prices:** [QORE_ALPHA2_FINAL_TSMOM_RISKSCALED_AND_XSREV5_FROZEN_PREREG_2026-10-12.md](QORE_ALPHA2_FINAL_TSMOM_RISKSCALED_AND_XSREV5_FROZEN_PREREG_2026-10-12.md), immutable ancestor commit `f9248d42a6cbced3d6e962b24e47c709cb91161c`. One fixed long-bottom7/short-top7 previous five common sessions, hold five common sessions, 1bp per side, DEV/DIAG, 4wk block bootstrap B2000 fixed seed 20261012. The historical panel had already been studied by other QORE methods, so not virgin OOS.
- #38319147236 **failed synthetic Ruff** only, no broker data opened. #38319216801 **synthetic PASS and original33 SHA/source extraction completed**, but a path-name mismatch in ephemeral SHA writer vs reader stopped FINISH; it did **not produce an economic result**. The integration correction `6226c6258e2ebfce843073f60eb2dab2b1fa7f22` changed **only** `{symbol}.sha256` to `{symbol}.json.sha256`, no rule/PnL thresholds; new synthetic integration/sidecar poisoning fixtures commit `13449860c358f0e47135209a9fa57cf5ee3dd01a`.
- The first GitHub Actions run from the corrected code was cancelled by an older, delayed workflow run's `cancel-in-progress` rule. Reran **only the cancelled original33 source job** from corrected HEAD, preserving frozen prereg/synthetic gate. [**GitHub Actions #38320167392 attempt 2**](https://github.com/mezas3238-hue/qore-core/actions/runs/38320167392), **COMPLETED SUCCESS**, HEAD `6226c6258e2ebfce843073f60eb2dab2b1fa7f22`. Synthetic Ruff and **9/9 tests PASS**; 12/12 CIBO Atlas + 21/21 ICMarkets original source workers executed in one ephemeral runner, verified original11-year RAW+QUALITY SHA and signed33 manifest; final combined rank result succeeded. No client broker requests, no real orders.
- **Original final panel GitHub artifact #11779086497**, `alpha2-XSREV5-ONE-GROSS_MINUS_ASSUMED_COST-6226c6258e2ebfce843073f60eb2dab2b1fa7f22`; downloaded ZIP checksum **SHA256 `419086e7d559a2b43f8050099621913e64a4ba23fab34c16addf512072fc2e08`**, independently verified against official GitHub artifact metadata, **PASS**. Inside, `OUTPUT_SHA256SUMS.txt` contains 2 signatures; both panel JSON `alpha2-xsrev5-33-one-gross-minus-assumed-cost.json` and `exact-code-head-sha.txt` independently rehashed **PASS**. Ephemeral daily source M5-aggregated price files **were NOT uploaded as artifact**, only derived selected rank/arm contribution/census and output hashes. This source audit is not a right to broker-labeled net execution.

## Exact frozen methodology

- Common all33 daily UTC calendar from original M5, Monday–Friday with at least 12 source M5 per symbol/day. No synthetic missing values; one missing canonical market removes the entire shared calendar date. **2068 dates** jointly eligible; individual canonical observed day counts range **2069–2084**, no market silently excluded.
- At first nonoverlapping eligible day of each ISO week, rank each market's previous 5 **COMMON** close-to-close simple return `close[t−1]/close[t−6]-1`, alphabetical fixed symbol tiebreak, 7 lowest LONG `+1/14`, 7 highest SHORT `−1/14`, other 19 cash. Sum(abs(weights))=1, sum(weights)=0. Entry at current day first M5 **OPEN reference**, exit last source M5 CLOSE of fifth common eligible day. Same UTC midnight potential zero-latency nonexecutable reference caveat as previous TSMOM, plus nonhomologated CFD account contract.
- Per-week gross = `sum((+/-1/14)*10000*(exit_close/entry_open-1))`; **fixed hypothetical 1bp/side** total `2bps` per completed portfolio entry+exit, irrespective of same-symbol re-entry next week. Cost-proxy = gross − 2bps (not true broker NET). Absence/censored weeks cash=0. Years 2016–2024 historical exposure, post-2024-09-17 embargo respected.
- Primary statistical gate: assumed-cost weekly mean>0 AND lower95% 4-week synchronized circular-block bootstrap>0 in **both** DEV and DIAG, and at least 52/26 active weeks. No subuniverse chosen from results, no parameter variant allowed after FAIL.

## Actual economic result — reference bps per calendar week, independent CI by synchronized 4week blocks

| Frozen measure | DEV [2016-09-17, 2022-09-17) | DIAG [2022-09-17, 2024-09-17) |
|---|---:|---:|
| Active original source common-week portfolios | **308** | **103** |
| Whole calendar weeks incl flat cash weeks | 314 | 106 |
| Week-power minimum 52 / 26 | PASS | PASS |
| Gross reference mean per calendar week | **+4.90004 bps** | **−0.06420 bps** |
| Gross minus *assumed 1bp each side* mean/week | **+2.93826 bps** | **−2.00760 bps** |
| CI95 4wk block for cost proxy bps/week | **[−5.13301; +12.36486]** | **[−15.13565; +11.55471]** |
| Gross mean per portfolio actually placed, before assumed fee | +4.99549bps | −0.06607bps |

**Total 411/411 frozen weekly portfolios**, 2068 common source dates, 3 censored end/era opportunities (`ERA_OR_EMBARGO_CENSORED=1`, `NOT_ENOUGH_FUTURE_COMMON_DAYS=2`). Weekly 4wk inference respects cross-market calendar clustering, not the 14 correlated legs as 14 IID observations. The calendar-week sample is substantially more informative than PATR/PADE's small independent-event samples, but both CIs are wide and span zero. DEV mean is positive, DIAG mean negative after assumed costs; **two-era prereg gate fails**.

## Independent ZIP readback invariants

An independent second consumer downloaded the original GitHub final ZIP and recomputed SHA256 of itself and 2 internal files. It parsed JSON and verified:
- **0/411 portfolios with wrong 7-long/7-short cardinality or overlapping legs.**
- **0/411 portfolios with non-2.0 bps assumed round-trip costs, gross != sum signed 14 arm contributions or cost-proxy != gross−2.0bps**.
- All 33 canonical included by date-intersection rule, no missing markets reweighted or alias-substituted; 2068 overlapping eligible days, raw source daily OHLC absent from output.
- Panel `status=XSREV5_GROSS_MINUS_ASSUMED_COST_FAIL`; `orders=0`, `UTC001_certified=false`, `COST_HYPOTHESIS_ONLY_NOT_REAL_BROKER_NET=true`.

### Inference boundaries and research conclusion

This **falsifies the predeclared two-era assumed-cost-positive screen for this exact all33 five-day contrarian strategy**, not the existence of all short-term reversal or financial time-series predictability. The DEV interval still includes positive/negative effects, and weekly strategy turnover, lack of broker BID/ASK as-of, account mismatch, execution zero-latency, swap/funding, shorts and portfolio risk cannot be certified from original OHLC. No PF/Sharpe/Sortino/DD NET can be asserted. No separate 'best 7' lists, profitable instrument carveouts, alternate lookback, ranks, vol-scaling, broker source or one-era-only promotions on these exposed years.

**CLOSED research lanes on the consumed 2016–2024 panel:**
- W1 PATR, W2 PADE: `INCONCLUSIVE_UNDERPOWERED`, not genuine edge falsations.
- W3 CMTRL: `PREDECLARED_GROSS_TEST_FAILED` for its specific prereg relative gross gate.
- TSMOM252 without risk-scaling: `TSMOM_EXPLORATORY_GROSS_SCREEN_FAIL`; not a canonical MOP replication.
- **FINAL TSMOM252 vol20 target10/cap3**: `FINAL_TSMOM_FAIL_CLOSE_FAMILY_ON_EXPOSED_DATA`, sector nonFX5 means positive but CI95 includes zero both eras, **NO confirmed sector edge**.
- **XSREV5 long bottom7/short top7**: `XSREV5_GROSS_MINUS_ASSUMED_COST_FAIL`, no net/execution/trader qualification.

**Next scientifically meaningful research** must prereg a genuinely **NEW independent temporal/asset holdout** and economic power before trading method iteration; no fresh "more signals" speculation on 2016–2024. In PARALLEL, #837 private authorized/license-compliant 728MB SHA verified archive+restore prior to original Atlas expiry **2026-12-16**, #868 genuine historical contract equivalence and #852 BIDASK entry-exit/account/cost/news PIT remain P0. **PR #840 DRAFT**, no merge/main/VPS/MT5/Shared/CIBO/QDLE/PAPER/LIVE/orders, **zero Alpha2 certified**.
